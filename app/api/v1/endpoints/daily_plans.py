from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.daily_work_plan import (
    DailyPlanHistoryItem,
    DailyPlanStatsResponse,
    DailyPlanWorkerAssignment,
    DailyWorkPlanCreate,
    DailyWorkPlanResponse,
    DailyWorkPlanUpdate,
    DailyWorkerAttendanceItem,
    DailyZoneTaskCreate,
    DailyZoneTaskResponse,
    DailyZoneTaskStatusUpdate,
)
from app.services.daily_plan_service import (
    add_zone_task,
    create_daily_plan,
    get_daily_plan,
    get_daily_plan_history,
    get_daily_plan_stats,
    get_plan_workers,
    get_today_plan,
    list_daily_plans,
    publish_daily_plan,
    save_attendance,
    update_daily_plan,
    update_zone_task_status,
)

router = APIRouter(prefix="/daily-plans", tags=["daily-plans"])


@router.post("/", response_model=ApiResponse[DailyWorkPlanResponse], status_code=status.HTTP_201_CREATED)
async def create_daily_plan_endpoint(
    payload: DailyWorkPlanCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    created = await create_daily_plan(db=db, created_by=current_user.id, payload=payload)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Daily work plan created successfully.",
        data=created,
    )


@router.post(
    "/{plan_id}/zones",
    response_model=ApiResponse[DailyZoneTaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_zone_task_endpoint(
    plan_id: uuid.UUID,
    payload: DailyZoneTaskCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyZoneTaskResponse]:
    created = await add_zone_task(db=db, plan_id=plan_id, payload=payload)
    return ApiResponse[DailyZoneTaskResponse](
        success=True,
        message="Zone task added successfully.",
        data=created,
    )


@router.post(
    "/{plan_id}/attendance",
    response_model=ApiResponse[DailyWorkPlanResponse],
    status_code=status.HTTP_200_OK,
)
async def save_attendance_endpoint(
    plan_id: uuid.UUID,
    payload: list[DailyWorkerAttendanceItem],
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    updated = await save_attendance(db=db, plan_id=plan_id, items=payload)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Worker attendance saved successfully.",
        data=updated,
    )


@router.post(
    "/{plan_id}/publish",
    response_model=ApiResponse[DailyWorkPlanResponse],
    status_code=status.HTTP_200_OK,
)
async def publish_daily_plan_endpoint(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    updated = await publish_daily_plan(db=db, plan_id=plan_id)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Daily work plan published successfully.",
        data=updated,
    )


@router.get("/today", response_model=ApiResponse[DailyWorkPlanResponse], status_code=status.HTTP_200_OK)
async def get_today_plan_endpoint(
    course_id: uuid.UUID = Query(...),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    plan = await get_today_plan(db=db, course_id=course_id)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Today's daily plan fetched successfully.",
        data=plan,
    )


@router.get(
    "/history",
    response_model=ApiResponse[list[DailyPlanHistoryItem]],
    status_code=status.HTTP_200_OK,
)
async def get_daily_plan_history_endpoint(
    course_id: uuid.UUID = Query(...),
    from_date: date | None = Query(default=None, alias="from_date"),
    to_date: date | None = Query(default=None, alias="to_date"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DailyPlanHistoryItem]]:
    history = await get_daily_plan_history(
        db=db,
        course_id=course_id,
        from_date=from_date,
        to_date=to_date,
    )
    return ApiResponse[list[DailyPlanHistoryItem]](
        success=True,
        message="Daily plan history fetched successfully.",
        data=history,
    )


@router.get(
    "/stats",
    response_model=ApiResponse[DailyPlanStatsResponse],
    status_code=status.HTTP_200_OK,
)
async def get_daily_plan_stats_endpoint(
    course_id: uuid.UUID = Query(...),
    month: str = Query(..., description="Month in YYYY-MM format"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyPlanStatsResponse]:
    stats = await get_daily_plan_stats(db=db, course_id=course_id, month=month)
    return ApiResponse[DailyPlanStatsResponse](
        success=True,
        message="Daily plan statistics fetched successfully.",
        data=stats,
    )


@router.get("/", response_model=ApiResponse[list[DailyWorkPlanResponse]], status_code=status.HTTP_200_OK)
async def list_daily_plans_endpoint(
    course_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    plan_status: str | None = Query(None, alias="status"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DailyWorkPlanResponse]]:
    plans = await list_daily_plans(
        db=db,
        course_id=course_id,
        date_from=date_from,
        date_to=date_to,
        plan_status=plan_status,
    )
    return ApiResponse[list[DailyWorkPlanResponse]](
        success=True,
        message="Daily plans fetched successfully.",
        data=plans,
    )


@router.get(
    "/{plan_id}/workers",
    response_model=ApiResponse[list[DailyPlanWorkerAssignment]],
    status_code=status.HTTP_200_OK,
)
async def get_plan_workers_endpoint(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DailyPlanWorkerAssignment]]:
    workers = await get_plan_workers(db=db, plan_id=plan_id)
    return ApiResponse[list[DailyPlanWorkerAssignment]](
        success=True,
        message="Plan workers fetched successfully.",
        data=workers,
    )


@router.get("/{plan_id}", response_model=ApiResponse[DailyWorkPlanResponse], status_code=status.HTTP_200_OK)
async def get_daily_plan_endpoint(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    plan = await get_daily_plan(db=db, plan_id=plan_id)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Daily plan fetched successfully.",
        data=plan,
    )


@router.patch("/{plan_id}", response_model=ApiResponse[DailyWorkPlanResponse], status_code=status.HTTP_200_OK)
async def update_daily_plan_endpoint(
    plan_id: uuid.UUID,
    payload: DailyWorkPlanUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyWorkPlanResponse]:
    updated = await update_daily_plan(db=db, plan_id=plan_id, payload=payload)
    return ApiResponse[DailyWorkPlanResponse](
        success=True,
        message="Daily plan updated successfully.",
        data=updated,
    )


@router.patch(
    "/zones/{zone_task_id}",
    response_model=ApiResponse[DailyZoneTaskResponse],
    status_code=status.HTTP_200_OK,
)
async def update_zone_task_status_endpoint(
    zone_task_id: uuid.UUID,
    payload: DailyZoneTaskStatusUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyZoneTaskResponse]:
    updated = await update_zone_task_status(
        db=db,
        zone_task_id=zone_task_id,
        payload=payload,
    )
    return ApiResponse[DailyZoneTaskResponse](
        success=True,
        message="Zone task status updated successfully.",
        data=updated,
    )
