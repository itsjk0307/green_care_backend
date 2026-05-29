from __future__ import annotations

import logging
import uuid
from collections import Counter
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
    DailyPlanHistoryItem,
    DailyPlanStatsResponse,
    DailyPlanWorkerAssignment,
    DailyWorkPlanCreate,
    DailyWorkPlanResponse,
    DailyWorkPlanUpdate,
    DailyWorkerAttendanceItem,
    DailyWorkerAttendanceResponse,
    DailyZoneTaskCreate,
    DailyZoneTaskResponse,
    DailyZoneTaskStatusUpdate,
)
from app.services.notification_service import create_notifications_for_users

logger = logging.getLogger(__name__)

_VALID_ZONE_STATUSES = {"pending", "in_progress", "done"}


def _parse_worker_ids(raw_ids: list[str]) -> list[uuid.UUID]:
    parsed: list[uuid.UUID] = []
    for raw in raw_ids:
        try:
            parsed.append(uuid.UUID(str(raw)))
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid worker id in zone task: {raw}",
            ) from error
    return parsed


def _collect_assigned_worker_ids(zone_tasks: list[DailyZoneTask]) -> list[uuid.UUID]:
    unique: set[uuid.UUID] = set()
    for task in zone_tasks:
        for worker_id in _parse_worker_ids(task.assigned_worker_ids):
            unique.add(worker_id)
    return sorted(unique, key=str)


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


async def publish_daily_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> DailyWorkPlanResponse:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )

    if plan.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft plans can be published.",
        )

    if not plan.zone_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one zone task is required before publishing.",
        )

    worker_ids = _collect_assigned_worker_ids(plan.zone_tasks)
    if not worker_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one worker must be assigned across zone tasks before publishing.",
        )

    plan.status = "published"
    plan_date_str = plan.plan_date.isoformat()

    await create_notifications_for_users(
        db,
        user_ids=worker_ids,
        notification_type="plan_published",
        title_ko="오늘의 작업 계획이 등록되었습니다",
        title_en="Today work plan has been published",
        body_ko=f"{plan_date_str} 작업 계획을 확인하세요",
        body_en=f"Check your work plan for {plan_date_str}",
        reference_id=plan.id,
        reference_type="daily_plan",
    )

    await db.commit()

    loaded = await _get_plan_loaded(db, plan_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load daily plan after publishing.",
        )
    logger.info("Daily plan published id=%s workers_notified=%s", plan_id, len(worker_ids))
    return _plan_to_response(loaded)


async def get_plan_workers(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> list[DailyPlanWorkerAssignment]:
    plan = await _get_plan_loaded(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily plan not found.",
        )

    worker_zones: dict[uuid.UUID, set[str]] = {}
    for task in plan.zone_tasks:
        for worker_id in _parse_worker_ids(task.assigned_worker_ids):
            worker_zones.setdefault(worker_id, set()).add(task.zone)

    if not worker_zones:
        return []

    result = await db.execute(select(User).where(User.id.in_(list(worker_zones.keys()))))
    users = {user.id: user for user in result.scalars().all()}

    assignments: list[DailyPlanWorkerAssignment] = []
    for worker_id, zones in sorted(worker_zones.items(), key=lambda item: str(item[0])):
        user = users.get(worker_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned worker not found: {worker_id}",
            )
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        assignments.append(
            DailyPlanWorkerAssignment(
                worker_id=worker_id,
                worker_name=user.name,
                worker_role=role,
                assigned_zones=sorted(zones),
            )
        )

    return assignments


async def get_daily_plan_history(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[DailyPlanHistoryItem]:
    await _ensure_course_exists(db, course_id)

    query = (
        select(DailyWorkPlan)
        .where(DailyWorkPlan.course_id == course_id)
        .options(selectinload(DailyWorkPlan.zone_tasks))
        .order_by(DailyWorkPlan.plan_date.desc())
    )
    if from_date is not None:
        query = query.where(DailyWorkPlan.plan_date >= from_date)
    if to_date is not None:
        query = query.where(DailyWorkPlan.plan_date <= to_date)

    result = await db.execute(query)
    plans = result.scalars().all()

    history: list[DailyPlanHistoryItem] = []
    for plan in plans:
        total_tasks = len(plan.zone_tasks)
        completed_tasks = sum(1 for task in plan.zone_tasks if task.status == "done")
        completion_pct = (
            round((completed_tasks / total_tasks) * 100.0, 2) if total_tasks > 0 else 0.0
        )
        history.append(
            DailyPlanHistoryItem(
                id=plan.id,
                plan_date=plan.plan_date,
                status=plan.status,
                weather=plan.weather,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                completion_pct=completion_pct,
                total_workers=plan.total_workers or 0,
            )
        )

    return history


async def get_daily_plan_stats(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    month: str,
) -> DailyPlanStatsResponse:
    await _ensure_course_exists(db, course_id)

    try:
        year_str, month_str = month.split("-", 1)
        year = int(year_str)
        mon = int(month_str)
        if mon < 1 or mon > 12:
            raise ValueError("month out of range")
        start = date(year, mon, 1)
        if mon == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, mon + 1, 1)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must be in YYYY-MM format.",
        ) from error

    result = await db.execute(
        select(DailyWorkPlan)
        .where(
            DailyWorkPlan.course_id == course_id,
            DailyWorkPlan.plan_date >= start,
            DailyWorkPlan.plan_date < end,
        )
        .options(
            selectinload(DailyWorkPlan.zone_tasks),
            selectinload(DailyWorkPlan.attendance),
        )
    )
    plans = result.scalars().all()

    plans_by_status: dict[str, int] = {"draft": 0, "published": 0, "completed": 0}
    completion_pcts: list[float] = []
    zone_counter: Counter[str] = Counter()
    task_counter: Counter[str] = Counter()
    total_worker_days = 0

    for plan in plans:
        status_key = plan.status if plan.status in plans_by_status else "draft"
        plans_by_status[status_key] = plans_by_status.get(status_key, 0) + 1

        total_tasks = len(plan.zone_tasks)
        completed_tasks = sum(1 for task in plan.zone_tasks if task.status == "done")
        completion_pcts.append(
            (completed_tasks / total_tasks) * 100.0 if total_tasks > 0 else 0.0
        )

        for task in plan.zone_tasks:
            zone_counter[task.zone] += 1
            for task_type in task.task_types:
                task_counter[str(task_type)] += 1

        total_worker_days += sum(
            1 for record in plan.attendance if record.status == "present"
        )

    avg_completion_pct = (
        round(sum(completion_pcts) / len(completion_pcts), 2) if completion_pcts else 0.0
    )
    most_common_zone = zone_counter.most_common(1)[0][0] if zone_counter else ""
    most_common_task = task_counter.most_common(1)[0][0] if task_counter else ""

    return DailyPlanStatsResponse(
        total_plans=len(plans),
        avg_completion_pct=avg_completion_pct,
        total_worker_days=total_worker_days,
        most_common_zone=most_common_zone,
        most_common_task=most_common_task,
        plans_by_status=plans_by_status,
    )
