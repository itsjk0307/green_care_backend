from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import UserRole
from app.models.work_report import WorkReport, WorkReportStatus
from app.schemas.work_report import (
    FieldPhotoResponse,
    WorkReportListResponse,
    WorkReportResponse,
    WorkReportReviewStatusLiteral,
)
from app.services.notification_service import create_notification
from app.services.storage_service import build_image_url

logger = logging.getLogger(__name__)


async def _get_work_report_loaded(
    db: AsyncSession,
    report_id: uuid.UUID,
) -> WorkReport | None:
    result = await db.execute(
        select(WorkReport)
        .where(WorkReport.id == report_id)
        .options(
            selectinload(WorkReport.worker),
            selectinload(WorkReport.course),
        ),
    )
    return result.scalar_one_or_none()


def _admin_like(role: str) -> bool:
    return role in {UserRole.admin.value, UserRole.manager.value}


def _to_field_photo_response(report: WorkReport) -> FieldPhotoResponse:
    image_url = build_image_url(report.before_image_path or "")
    return FieldPhotoResponse(
        id=report.id,
        worker_name=report.worker.name if report.worker else "",
        gps_latitude=report.gps_latitude,
        gps_longitude=report.gps_longitude,
        image_url=image_url,
        notes=report.notes,
        created_at=report.created_at,
        status=report.status.value,
    )


async def create_work_report(
    db: AsyncSession,
    worker_id: uuid.UUID,
    course_id: uuid.UUID,
    work_types: list[str],
    before_image_path: str,
    zone_coordinates: list[dict[str, Any]] | None,
    mark_type: str | None,
    pin_x: float | None,
    pin_y: float | None,
    gps_latitude: float | None,
    gps_longitude: float | None,
    notes: str | None,
) -> WorkReportResponse:
    report = WorkReport(
        worker_id=worker_id,
        course_id=course_id,
        work_types=work_types,
        before_image_path=before_image_path,
        zone_coordinates=zone_coordinates,
        mark_type=mark_type,
        pin_x=pin_x,
        pin_y=pin_y,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        notes=notes,
        status=WorkReportStatus.in_progress,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    loaded = await _get_work_report_loaded(db, report.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created work report.",
        )
    logger.info(
        "Work report created id=%s worker_id=%s course_id=%s",
        loaded.id,
        worker_id,
        course_id,
    )
    return WorkReportResponse.model_validate(loaded)


async def create_field_photo_report(
    db: AsyncSession,
    worker_id: uuid.UUID,
    course_id: uuid.UUID,
    gps_latitude: float,
    gps_longitude: float,
    image_path: str,
    notes: str | None,
) -> FieldPhotoResponse:
    report = WorkReport(
        worker_id=worker_id,
        course_id=course_id,
        work_types=["field_photo"],
        before_image_path=image_path,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        notes=notes,
        status=WorkReportStatus.in_progress,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    loaded = await _get_work_report_loaded(db, report.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created field photo report.",
        )
    logger.info(
        "Field photo report created id=%s worker_id=%s course_id=%s",
        loaded.id,
        worker_id,
        course_id,
    )
    return _to_field_photo_response(loaded)


async def get_field_photos(
    db: AsyncSession,
    course_id: uuid.UUID,
) -> list[FieldPhotoResponse]:
    result = await db.execute(
        select(WorkReport)
        .where(
            WorkReport.course_id == course_id,
            WorkReport.work_types.contains(["field_photo"]),
        )
        .options(selectinload(WorkReport.worker))
        .order_by(WorkReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [_to_field_photo_response(r) for r in reports]


async def complete_work_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    worker_id: uuid.UUID,
    after_image_path: str,
    gps_route: list[dict[str, Any]] | None,
    notes: str | None,
) -> WorkReportResponse:
    report = await _get_work_report_loaded(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )
    if report.worker_id != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this work report.",
        )
    if report.status != WorkReportStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only in-progress work reports can be completed.",
        )

    report.after_image_path = after_image_path
    report.gps_route = gps_route
    if notes is not None:
        report.notes = notes
    report.completed_at = datetime.now(timezone.utc)
    report.status = WorkReportStatus.pending

    await db.commit()
    loaded = await _get_work_report_loaded(db, report_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated work report.",
        )
    logger.info("Work report completed id=%s worker_id=%s", report_id, worker_id)
    return WorkReportResponse.model_validate(loaded)


async def get_work_reports(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: str,
    course_id: uuid.UUID | None,
    status_filter: str | None,
    page: int,
    limit: int,
) -> WorkReportListResponse:
    filters: list = []

    if role == UserRole.worker.value:
        filters.append(WorkReport.worker_id == user_id)
    elif not _admin_like(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list work reports.",
        )

    if course_id is not None:
        filters.append(WorkReport.course_id == course_id)

    if status_filter:
        try:
            filters.append(WorkReport.status == WorkReportStatus(status_filter))
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid work report status filter.",
            ) from err

    count_q = select(func.count(WorkReport.id))
    if filters:
        count_q = count_q.where(*filters)
    total_result = await db.execute(count_q)
    total = int(total_result.scalar_one() or 0)

    q = (
        select(WorkReport)
        .options(
            selectinload(WorkReport.worker),
            selectinload(WorkReport.course),
        )
        .order_by(WorkReport.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if filters:
        q = q.where(*filters)

    result = await db.execute(q)
    reports = result.scalars().all()

    return WorkReportListResponse(
        reports=[WorkReportResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        limit=limit,
    )


async def get_work_report_by_id(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> WorkReportResponse:
    report = await _get_work_report_loaded(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )
    if role == UserRole.worker.value and report.worker_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this work report.",
        )
    if not _admin_like(role) and role != UserRole.worker.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this work report.",
        )

    return WorkReportResponse.model_validate(report)


async def update_work_report_status(
    db: AsyncSession,
    report_id: uuid.UUID,
    status_value: WorkReportReviewStatusLiteral,
    admin_user_id: uuid.UUID,
) -> WorkReportResponse:
    report = await _get_work_report_loaded(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work report not found.",
        )
    if report.status != WorkReportStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending work reports can be approved or rejected.",
        )

    new_status = (
        WorkReportStatus.approved
        if status_value == "approved"
        else WorkReportStatus.rejected
    )
    report.status = new_status
    report.approved_by = admin_user_id
    report.reviewed_at = datetime.now(timezone.utc)

    if status_value == "approved":
        await create_notification(
            db,
            user_id=report.worker_id,
            notification_type="report_approved",
            title_ko="작업 보고서가 승인되었습니다",
            title_en="Your work report was approved",
            body_ko="제출하신 작업 보고서가 승인되었습니다.",
            body_en="Your submitted work report has been approved.",
            reference_id=report.id,
            reference_type="work_report",
        )
    elif status_value == "rejected":
        await create_notification(
            db,
            user_id=report.worker_id,
            notification_type="report_rejected",
            title_ko="작업 보고서가 반려되었습니다",
            title_en="Your work report was rejected",
            body_ko="제출하신 작업 보고서가 반려되었습니다.",
            body_en="Your submitted work report has been rejected.",
            reference_id=report.id,
            reference_type="work_report",
        )

    await db.commit()
    loaded = await _get_work_report_loaded(db, report_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated work report.",
        )
    logger.info(
        "Work report status updated id=%s status=%s admin_id=%s",
        report_id,
        status_value,
        admin_user_id,
    )
    return WorkReportResponse.model_validate(loaded)
