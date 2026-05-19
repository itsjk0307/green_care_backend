from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_work_plan import (
    DailyWorkerAttendance,
    DailyWorkPlan,
    DailyZoneTask,
)
from app.models.golf_course import GolfCourse
from app.models.user import User
from app.schemas.daily_work_plan import (
    DailyWorkPlanCreate,
    DailyWorkPlanResponse,
    DailyWorkPlanUpdate,
    DailyWorkerAttendanceItem,
    DailyWorkerAttendanceResponse,
    DailyZoneTaskCreate,
    DailyZoneTaskResponse,
    DailyZoneTaskStatusUpdate,
)

logger = logging.getLogger(__name__)

_VALID_ZONE_STATUSES = {"pending", "in_progress", "done"}


async def _get_plan_loaded(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> DailyWorkPlan | None:
    result = await db.execute(
        select(DailyWorkPlan)
        .where(DailyWorkPlan.id == plan_id)
        .options(
            selectinload(DailyWorkPlan.zone_tasks),
            selectinload(DailyWorkPlan.attendance),
        ),
    )
    return result.scalar_one_or_none()


def _plan_to_response(plan: DailyWorkPlan) -> DailyWorkPlanResponse:
    zone_tasks = [
        DailyZoneTaskResponse.model_validate(t) for t in plan.zone_tasks
    ]
    attendance = [
        DailyWorkerAttendanceResponse.model_validate(a) for a in plan.attendance
    ]
    data = DailyWorkPlanResponse.model_validate(plan)
    return data.model_copy(update={"zone_tasks": zone_tasks, "attendance": attendance})


async def _ensure_course_exists(db: AsyncSession, course_id: uuid.UUID) -> None:
    result = await db.execute(
        select(GolfCourse.id).where(GolfCourse.id == course_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )


async def create_daily_plan(
    db: AsyncSession,
    created_by: uuid.UUID,
    payload: DailyWorkPlanCreate,
) -> DailyWorkPlanResponse:
    await _ensure_course_exists(db, payload.course_id)

    existing = await db.execute(
        select(DailyWorkPlan).where(
            DailyWorkPlan.course_id == payload.course_id,
            DailyWorkPlan.plan_date == payload.plan_date,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A daily plan already exists for this course and date.",
        )

    plan = DailyWorkPlan(
        course_id=payload.course_id,
        created_by=created_by,
        plan_date=payload.plan_date,
        weather=payload.weather,
        temperature_min=payload.temperature_min,
        temperature_max=payload.temperature_max,
        rainfall_mm=payload.rainfall_mm,
        special_notes=payload.special_notes,
        status="draft",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    loaded = await _get_plan_loaded(db, plan.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created daily plan.",
        )
    logger.info("Daily plan created id=%s course_id=%s", loaded.id, payload.course_id)
    return _plan_to_response(loaded)


async def add_zone_task(
    db: AsyncSession,
    plan_id: uuid.UUID,
    payload: DailyZoneTaskCreate,
) -> DailyZoneTaskResponse:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )

    task = DailyZoneTask(
        plan_id=plan_id,
        zone=payload.zone,
        task_types=payload.task_types,
        mowing_height_mm=payload.mowing_height_mm,
        assigned_worker_ids=[str(wid) for wid in payload.assigned_worker_ids],
        notes=payload.notes,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return DailyZoneTaskResponse.model_validate(task)


async def save_attendance(
    db: AsyncSession,
    plan_id: uuid.UUID,
    items: list[DailyWorkerAttendanceItem],
) -> DailyWorkPlanResponse:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )

    worker_ids = [item.worker_id for item in items]
    if worker_ids:
        result = await db.execute(select(User.id).where(User.id.in_(worker_ids)))
        found = {row[0] for row in result.all()}
        missing = [wid for wid in worker_ids if wid not in found]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown worker id(s): {missing}",
            )

    for record in list(plan.attendance):
        await db.delete(record)
    await db.flush()

    present_count = 0
    for item in items:
        db.add(
            DailyWorkerAttendance(
                plan_id=plan_id,
                worker_id=item.worker_id,
                status=item.status,
                start_time=item.start_time,
                end_time=item.end_time,
                working_hours=item.working_hours,
            )
        )
        if item.status == "present":
            present_count += 1

    plan.total_workers = present_count
    await db.commit()

    loaded = await _get_plan_loaded(db, plan_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load daily plan after saving attendance.",
        )
    return _plan_to_response(loaded)


async def get_today_plan(
    db: AsyncSession,
    course_id: uuid.UUID,
) -> DailyWorkPlanResponse:
    today = date.today()
    result = await db.execute(
        select(DailyWorkPlan)
        .where(
            DailyWorkPlan.course_id == course_id,
            DailyWorkPlan.plan_date == today,
        )
        .options(
            selectinload(DailyWorkPlan.zone_tasks),
            selectinload(DailyWorkPlan.attendance),
        ),
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily plan found for today.",
        )
    return _plan_to_response(plan)


async def list_daily_plans(
    db: AsyncSession,
    course_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    plan_status: str | None = None,
) -> list[DailyWorkPlanResponse]:
    query = select(DailyWorkPlan).options(
        selectinload(DailyWorkPlan.zone_tasks),
        selectinload(DailyWorkPlan.attendance),
    )

    if course_id is not None:
        query = query.where(DailyWorkPlan.course_id == course_id)
    if date_from is not None:
        query = query.where(DailyWorkPlan.plan_date >= date_from)
    if date_to is not None:
        query = query.where(DailyWorkPlan.plan_date <= date_to)
    if plan_status is not None:
        query = query.where(DailyWorkPlan.status == plan_status)

    query = query.order_by(DailyWorkPlan.plan_date.desc())
    result = await db.execute(query)
    plans = result.scalars().all()
    return [_plan_to_response(p) for p in plans]


async def get_daily_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> DailyWorkPlanResponse:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )
    return _plan_to_response(plan)


async def update_daily_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
    payload: DailyWorkPlanUpdate,
) -> DailyWorkPlanResponse:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(plan, field, value)

    await db.commit()
    loaded = await _get_plan_loaded(db, plan_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated daily plan.",
        )
    return _plan_to_response(loaded)


async def update_zone_task_status(
    db: AsyncSession,
    zone_task_id: uuid.UUID,
    payload: DailyZoneTaskStatusUpdate,
) -> DailyZoneTaskResponse:
    result = await db.execute(
        select(DailyZoneTask).where(DailyZoneTask.id == zone_task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone task not found.",
        )

    if payload.status not in _VALID_ZONE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(_VALID_ZONE_STATUSES)}",
        )

    task.status = payload.status
    if payload.status == "done":
        task.completed_at = datetime.now(timezone.utc)
    elif payload.status in {"pending", "in_progress"}:
        task.completed_at = None

    await db.commit()
    await db.refresh(task)
    return DailyZoneTaskResponse.model_validate(task)
