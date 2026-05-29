from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.drone_scan import (
    DroneScanDetailResponse,
    DroneScanResponse,
    ScanResultResponse,
)
from app.services.drone_scan_service import (
    analyze_drone_scan,
    create_drone_scan,
    get_drone_scan_detail,
    get_latest_completed_scan,
    get_scan_results_for_course,
    list_drone_scans,
)
from app.services.storage_service import save_drone_scan_image

drone_scans_router = APIRouter(prefix="/drone-scans", tags=["drone-scans"])
scan_results_router = APIRouter(prefix="/scan-results", tags=["scan-results"])


@drone_scans_router.post(
    "/",
    response_model=ApiResponse[DroneScanResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_drone_scan_endpoint(
    course_id: uuid.UUID = Form(...),
    scan_date: date = Form(...),
    notes: str | None = Form(default=None),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DroneScanResponse]:
    if image.filename is None or image.filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is required.",
        )

    image_path, image_width, image_height = await save_drone_scan_image(image, scan_date)

    data = await create_drone_scan(
        db=db,
        course_id=course_id,
        uploaded_by=current_user.id,
        scan_date=scan_date,
        image_path=image_path,
        image_width=image_width,
        image_height=image_height,
        notes=notes,
    )
    return ApiResponse[DroneScanResponse](
        success=True,
        message="Drone scan uploaded successfully.",
        data=data,
    )


@drone_scans_router.post(
    "/{scan_id}/analyze",
    response_model=ApiResponse[DroneScanDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def analyze_drone_scan_endpoint(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DroneScanDetailResponse]:
    _ = current_user
    data = await analyze_drone_scan(db=db, scan_id=scan_id)
    return ApiResponse[DroneScanDetailResponse](
        success=True,
        message="Drone scan analysis completed successfully.",
        data=data,
    )


@drone_scans_router.get(
    "/",
    response_model=ApiResponse[list[DroneScanResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_drone_scans_endpoint(
    course_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DroneScanResponse]]:
    _ = current_user
    data = await list_drone_scans(db=db, course_id=course_id)
    return ApiResponse[list[DroneScanResponse]](
        success=True,
        message="Drone scans fetched successfully.",
        data=data,
    )


@drone_scans_router.get(
    "/latest",
    response_model=ApiResponse[DroneScanDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def get_latest_drone_scan_endpoint(
    course_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DroneScanDetailResponse]:
    _ = current_user
    data = await get_latest_completed_scan(db=db, course_id=course_id)
    return ApiResponse[DroneScanDetailResponse](
        success=True,
        message="Latest completed drone scan fetched successfully.",
        data=data,
    )


@drone_scans_router.get(
    "/{scan_id}",
    response_model=ApiResponse[DroneScanDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def get_drone_scan_endpoint(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DroneScanDetailResponse]:
    _ = current_user
    data = await get_drone_scan_detail(db=db, scan_id=scan_id)
    return ApiResponse[DroneScanDetailResponse](
        success=True,
        message="Drone scan fetched successfully.",
        data=data,
    )


@scan_results_router.get(
    "/",
    response_model=ApiResponse[list[ScanResultResponse]],
    status_code=status.HTTP_200_OK,
)
async def get_scan_results_endpoint(
    course_id: uuid.UUID = Query(...),
    hole: int | None = Query(default=None, ge=1, le=18),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ScanResultResponse]]:
    _ = current_user
    data = await get_scan_results_for_course(db=db, course_id=course_id, hole=hole)
    return ApiResponse[list[ScanResultResponse]](
        success=True,
        message="Scan results fetched successfully.",
        data=data,
    )
