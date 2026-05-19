from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.work_area import WorkAreaResponse
from app.services.work_area_service import list_work_areas

router = APIRouter(prefix="/work-areas", tags=["map_areas"])


@router.get("/", response_model=ApiResponse[list[WorkAreaResponse]], status_code=status.HTTP_200_OK)
async def list_work_areas_endpoint(
    course_id: uuid.UUID | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[WorkAreaResponse]]:
    areas = await list_work_areas(db=db, course_id=course_id)
    return ApiResponse[list[WorkAreaResponse]](
        success=True,
        message="Work areas fetched successfully.",
        data=areas,
    )
