from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.photobox import HolePhotoSummaryResponse, PhotoListResponse
from app.services.photobox_service import get_photos_by_hole, list_photos

photobox_router = APIRouter(prefix="/photos", tags=["photobox"])


@photobox_router.get(
    "/",
    response_model=ApiResponse[PhotoListResponse],
    status_code=status.HTTP_200_OK,
)
async def list_photos_endpoint(
    course_id: uuid.UUID = Query(...),
    hole_number: int | None = Query(default=None, ge=1, le=18),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    work_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PhotoListResponse]:
    _ = current_user
    data = await list_photos(
        db=db,
        course_id=course_id,
        hole_number=hole_number,
        from_date=from_date,
        to_date=to_date,
        work_type=work_type,
        page=page,
        per_page=per_page,
    )
    return ApiResponse[PhotoListResponse](
        success=True,
        message="Photos fetched successfully.",
        data=data,
    )


@photobox_router.get(
    "/by-hole",
    response_model=ApiResponse[list[HolePhotoSummaryResponse]],
    status_code=status.HTTP_200_OK,
)
async def get_photos_by_hole_endpoint(
    course_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[HolePhotoSummaryResponse]]:
    _ = current_user
    data = await get_photos_by_hole(db=db, course_id=course_id)
    return ApiResponse[list[HolePhotoSummaryResponse]](
        success=True,
        message="Hole photo summaries fetched successfully.",
        data=data,
    )
