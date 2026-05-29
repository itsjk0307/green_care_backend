from __future__ import annotations

import logging
import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_strict_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.golf_course import (
    CourseMapUploadResponse,
    GolfCourseCreate,
    GolfCourseResponse,
    GolfCourseUpdate,
)
from app.services.golf_course_service import (
    create_course,
    get_all_courses,
    get_course_by_id,
    get_course_model_by_id,
    update_course,
)
from app.services.storage_service import FIELD_PHOTO_EXTENSIONS, _read_and_validate, _storage_root

router = APIRouter(prefix="/courses", tags=["courses"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ApiResponse[GolfCourseResponse], status_code=201)
async def create_course_endpoint(
    payload: GolfCourseCreate,
    _: User = Depends(get_current_strict_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[GolfCourseResponse]:
    course = await create_course(db=db, data=payload)
    return ApiResponse[GolfCourseResponse](
        success=True,
        message="Golf course created successfully.",
        data=course,
    )


@router.get("/", response_model=ApiResponse[list[GolfCourseResponse]], status_code=200)
async def list_courses_endpoint(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[GolfCourseResponse]]:
    courses = await get_all_courses(db=db)
    return ApiResponse[list[GolfCourseResponse]](
        success=True,
        message="Golf courses fetched successfully.",
        data=courses,
    )


@router.get("/{course_id}/map")
async def get_course_map(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    course = await get_course_model_by_id(db, course_id)

    if not course or not course.map_image_path:
        raise HTTPException(
            status_code=404,
            detail="No map found for this course",
        )

    map_path = os.path.join(
        "storage",
        "maps",
        course.map_image_path,
    )

    if not os.path.exists(map_path):
        raise HTTPException(
            status_code=404,
            detail="Map file not found on server",
        )

    return FileResponse(
        path=map_path,
        media_type="image/jpeg",
    )


@router.post(
    "/{course_id}/map",
    response_model=ApiResponse[CourseMapUploadResponse],
    status_code=200,
)
async def upload_course_map(
    course_id: uuid.UUID,
    map_image: UploadFile = File(...),
    _: User = Depends(get_current_strict_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CourseMapUploadResponse]:
    course = await get_course_model_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Golf course not found.")

    original_filename = map_image.filename or ""
    content = await _read_and_validate(map_image, FIELD_PHOTO_EXTENSIONS, label="map image")

    maps_dir = _storage_root() / "maps"
    os.makedirs(str(maps_dir), exist_ok=True)

    saved_name = f"{course_id}.jpg"
    try:
        async with aiofiles.open(maps_dir / saved_name, "wb") as out:
            await out.write(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save map image to storage.",
        ) from exc

    course.map_image_path = saved_name
    await db.commit()
    await db.refresh(course)

    map_url = f"/storage/maps/{saved_name}"
    logger.info("Uploaded map for course id=%s -> %s", course_id, map_url)

    return ApiResponse[CourseMapUploadResponse](
        success=True,
        message="Course map uploaded successfully.",
        data=CourseMapUploadResponse(
            course_id=str(course_id),
            map_url=map_url,
            filename=original_filename,
        ),
    )


@router.get("/{course_id}", response_model=ApiResponse[GolfCourseResponse], status_code=200)
async def get_course_endpoint(
    course_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[GolfCourseResponse]:
    course = await get_course_by_id(db=db, course_id=course_id)
    return ApiResponse[GolfCourseResponse](
        success=True,
        message="Golf course fetched successfully.",
        data=course,
    )


@router.patch("/{course_id}", response_model=ApiResponse[GolfCourseResponse], status_code=200)
async def update_course_endpoint(
    course_id: uuid.UUID,
    payload: GolfCourseUpdate,
    _: User = Depends(get_current_strict_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[GolfCourseResponse]:
    course = await update_course(db=db, course_id=course_id, data=payload)
    return ApiResponse[GolfCourseResponse](
        success=True,
        message="Golf course updated successfully.",
        data=course,
    )
