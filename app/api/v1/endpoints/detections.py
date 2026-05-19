from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_strict_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.detection_report import (
    DetectionCreate,
    DetectionListResponse,
    DetectionReportResponse,
    DetectionStatusUpdate,
)
from app.services.detection_service import (
    create_detection,
    get_detection_by_id,
    get_detections,
    update_detection_status,
)
from app.services.storage_service import save_detection_images

router = APIRouter(prefix="/detections", tags=["detections"])

EXACTLY_SIX_IMAGES_MSG = "Exactly 6 images required for disease detection analysis"


def _parse_zone_coordinates(value: str | None) -> list[dict] | None:
    if value is None or value.strip() == "":
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON for zone_coordinates.",
        ) from err
    if parsed is None:
        return None
    if not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zone_coordinates must be a JSON array of objects.",
        )
    return parsed


@router.post("/", response_model=ApiResponse[DetectionReportResponse], status_code=status.HTTP_201_CREATED)
async def create_detection_endpoint(
    course_id: uuid.UUID = Form(...),
    zone_coordinates: str | None = Form(default=None),
    pin_x: float | None = Form(default=None),
    pin_y: float | None = Form(default=None),
    gps_latitude: float | None = Form(default=None),
    gps_longitude: float | None = Form(default=None),
    upload_source: str = Form(...),
    drone_height_m: float | None = Form(default=None),
    images: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DetectionReportResponse]:
    if len(images) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EXACTLY_SIX_IMAGES_MSG,
        )

    zc = _parse_zone_coordinates(zone_coordinates)
    payload = DetectionCreate.model_validate(
        {
            "course_id": course_id,
            "zone_coordinates": zc,
            "pin_x": pin_x,
            "pin_y": pin_y,
            "gps_latitude": gps_latitude,
            "gps_longitude": gps_longitude,
            "upload_source": upload_source,
            "drone_height_m": drone_height_m,
        }
    )

    detection_id = uuid.uuid4()
    saved = await save_detection_images(images, detection_id)
    paths = [pair[0] for pair in saved]
    sizes = [pair[1] for pair in saved]

    data = await create_detection(
        db=db,
        uploaded_by=current_user.id,
        course_id=payload.course_id,
        detection_id=detection_id,
        image_paths=paths,
        file_sizes_mb=sizes,
        zone_coordinates=payload.zone_coordinates,
        pin_x=payload.pin_x,
        pin_y=payload.pin_y,
        gps_latitude=payload.gps_latitude,
        gps_longitude=payload.gps_longitude,
        upload_source=payload.upload_source,
        drone_height_m=payload.drone_height_m,
    )
    return ApiResponse[DetectionReportResponse](
        success=True,
        message="Detection analysis completed successfully.",
        data=data,
    )


@router.get("/", response_model=ApiResponse[DetectionListResponse], status_code=status.HTTP_200_OK)
async def list_detections_endpoint(
    course_id: uuid.UUID | None = Query(default=None),
    condition: str | None = Query(default=None, description="good | disease_found | processing"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DetectionListResponse]:
    result = await get_detections(
        db=db,
        user_id=current_user.id,
        role=current_user.role.value,
        course_id=course_id,
        condition_filter=condition,
        page=page,
        limit=limit,
    )
    return ApiResponse[DetectionListResponse](
        success=True,
        message="Detections fetched successfully.",
        data=result,
    )


@router.get("/{detection_id}", response_model=ApiResponse[DetectionReportResponse], status_code=status.HTTP_200_OK)
async def get_detection_endpoint(
    detection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DetectionReportResponse]:
    row = await get_detection_by_id(
        db=db,
        detection_id=detection_id,
        user_id=current_user.id,
        role=current_user.role.value,
    )
    return ApiResponse[DetectionReportResponse](
        success=True,
        message="Detection fetched successfully.",
        data=row,
    )


@router.patch(
    "/{detection_id}/status",
    response_model=ApiResponse[DetectionReportResponse],
    status_code=status.HTTP_200_OK,
)
async def update_detection_status_endpoint(
    detection_id: uuid.UUID,
    payload: DetectionStatusUpdate,
    admin_user: User = Depends(get_current_strict_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DetectionReportResponse]:
    updated = await update_detection_status(
        db=db,
        detection_id=detection_id,
        status_value=payload.status,
        admin_user_id=admin_user.id,
    )
    return ApiResponse[DetectionReportResponse](
        success=True,
        message="Detection status updated successfully.",
        data=updated,
    )
