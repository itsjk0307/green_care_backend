from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_result import AIResult, SeverityLevel
from app.models.report import Report, ReportStatus, TaskType
from app.models.user import UserRole
from app.schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportStatusReviewOnly,
)
from app.services.ai_service import analyze_images, get_disease_display_name

logger = logging.getLogger(__name__)


async def _get_report_with_relations(
    db: AsyncSession,
    report_id: uuid.UUID,
) -> Report | None:
    query = (
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.user),
            selectinload(Report.ai_result),
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    report_data: ReportCreate,
    image_path: str,
) -> ReportResponse:
    logger.info("Creating report for user_id=%s", user_id)
    report = Report(
        user_id=user_id,
        task_type=TaskType(report_data.task_type),
        latitude=report_data.latitude,
        longitude=report_data.longitude,
        location_name=report_data.location_name,
        notes=report_data.notes,
        image_path=image_path,
        status=ReportStatus.pending,
    )
    db.add(report)
    await db.flush()

    ai_output = await analyze_images([image_path] * 6)
    logger.info(
        "AI analysis result report_id=%s condition=%s disease=%s confidence=%s",
        report.id,
        ai_output["condition"],
        ai_output["disease_type"],
        ai_output["confidence"],
    )
    disease_detected = ai_output["condition"] == "disease_found"
    disease_type_label = (
        get_disease_display_name(ai_output["disease_type"], "en")
        if ai_output["disease_type"]
        else None
    )
    ai_result = AIResult(
        report_id=report.id,
        disease_detected=disease_detected,
        disease_type=disease_type_label,
        confidence=ai_output["confidence"],
        severity=SeverityLevel(ai_output["severity"]) if ai_output["severity"] else None,
        affected_area_percent=(
            ai_output["affected_area_percent"]
            if ai_output["affected_area_percent"]
            else None
        ),
        bounding_boxes=None,
        recommendation=ai_output["recommendation_en"],
        model_version=ai_output["model_version"],
        processed_at=datetime.now(timezone.utc),
    )
    db.add(ai_result)

    await db.commit()
    refreshed_report = await _get_report_with_relations(db, report.id)
    if refreshed_report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch created report.",
        )
    return ReportResponse.model_validate(refreshed_report)


async def get_reports(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: str,
    status_filter: str | None,
    page: int,
    limit: int,
) -> ReportListResponse:
    logger.info(
        "Fetching reports user_id=%s role=%s status=%s page=%s limit=%s",
        user_id,
        role,
        status_filter,
        page,
        limit,
    )
    filters = []

    if role == UserRole.worker.value:
        filters.append(Report.user_id == user_id)

    if status_filter:
        filters.append(Report.status == ReportStatus(status_filter))

    count_query = select(func.count(Report.id))
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one() or 0)

    query = (
        select(Report)
        .options(selectinload(Report.user), selectinload(Report.ai_result))
        .order_by(Report.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if filters:
        query = query.where(*filters)

    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[ReportResponse.model_validate(report) for report in reports],
        total=total,
        page=page,
        limit=limit,
    )


async def get_report_by_id(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> ReportResponse:
    logger.info("Fetching report by id report_id=%s for user_id=%s role=%s", report_id, user_id, role)
    report = await _get_report_with_relations(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if role == UserRole.worker.value and report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this report.",
        )

    return ReportResponse.model_validate(report)


async def update_report_status(
    db: AsyncSession,
    report_id: uuid.UUID,
    status_value: ReportStatusReviewOnly,
    admin_user_id: uuid.UUID,
) -> ReportResponse:
    logger.info(
        "Updating report status report_id=%s status=%s admin_user_id=%s",
        report_id,
        status_value,
        admin_user_id,
    )
    report = await _get_report_with_relations(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    report.status = ReportStatus(status_value)
    report.reviewed_by = admin_user_id
    report.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    refreshed_report = await _get_report_with_relations(db, report_id)
    if refreshed_report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch updated report.",
        )
    return ReportResponse.model_validate(refreshed_report)

