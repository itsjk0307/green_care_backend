from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_result import SeverityLevel
from app.models.detection_report import (
    DetectionCondition,
    DetectionImage,
    DetectionImageAngle,
    DetectionReport,
    DetectionReportStatus,
    DetectionUploadSource,
)
from app.models.user import UserRole
from app.schemas.detection_report import DetectionListResponse, DetectionReportResponse
from app.services.ai_service import analyze_images

logger = logging.getLogger(__name__)

_DETECTION_IMAGE_ANGLES: tuple[DetectionImageAngle, ...] = (
    DetectionImageAngle.top,
    DetectionImageAngle.center,
    DetectionImageAngle.bottom,
    DetectionImageAngle.left,
    DetectionImageAngle.right,
    DetectionImageAngle.close_up,
)


def _admin_like(role: str) -> bool:
    return role in {UserRole.admin.value, UserRole.manager.value}


async def _get_detection_loaded(
    db: AsyncSession,
    detection_id: uuid.UUID,
) -> DetectionReport | None:
    result = await db.execute(
        select(DetectionReport)
        .where(DetectionReport.id == detection_id)
        .options(
            selectinload(DetectionReport.images),
            selectinload(DetectionReport.uploader),
            selectinload(DetectionReport.course),
        ),
    )
    return result.scalar_one_or_none()


def _sort_images(images: list) -> list:
    return sorted(images, key=lambda im: im.image_path)


async def create_detection(
    db: AsyncSession,
    uploaded_by: uuid.UUID,
    course_id: uuid.UUID,
    detection_id: uuid.UUID,
    image_paths: list[str],
    file_sizes_mb: list[float],
    zone_coordinates: list[dict[str, Any]] | None,
    pin_x: float | None,
    pin_y: float | None,
    gps_latitude: float | None,
    gps_longitude: float | None,
    upload_source: str,
    drone_height_m: float | None,
) -> DetectionReportResponse:
    if len(image_paths) != 6 or len(file_sizes_mb) != 6:
        raise ValueError("create_detection requires exactly 6 image paths and 6 file sizes")

    report = DetectionReport(
        id=detection_id,
        uploaded_by=uploaded_by,
        course_id=course_id,
        zone_coordinates=zone_coordinates,
        pin_x=pin_x,
        pin_y=pin_y,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        upload_source=DetectionUploadSource(upload_source),
        drone_height_m=drone_height_m,
        condition=DetectionCondition.processing,
        status=DetectionReportStatus.processing,
        ai_model_version="mock-1.0.0",
    )
    db.add(report)
    await db.flush()

    for index, path in enumerate(image_paths):
        db.add(
            DetectionImage(
                detection_report_id=detection_id,
                image_path=path,
                angle=_DETECTION_IMAGE_ANGLES[index],
                file_size_mb=file_sizes_mb[index],
            ),
        )
    await db.flush()

    ai_result = await analyze_images(list(image_paths))

    report.condition = DetectionCondition(ai_result["condition"])
    report.disease_type = ai_result.get("disease_type")
    report.confidence = ai_result.get("confidence")
    if ai_result.get("severity"):
        report.severity = SeverityLevel(ai_result["severity"])
    else:
        report.severity = None
    pct = ai_result.get("affected_area_percent")
    report.affected_area_percent = float(pct) if pct is not None else None
    report.recommendation_en = ai_result.get("recommendation_en")
    report.recommendation_ko = ai_result.get("recommendation_ko")
    report.ai_model_version = ai_result["model_version"]
    report.status = DetectionReportStatus.completed
    report.processed_at = datetime.now(timezone.utc)

    await db.commit()

    loaded = await _get_detection_loaded(db, detection_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load detection report after creation.",
        )
    logger.info(
        "Detection created id=%s condition=%s uploaded_by=%s",
        detection_id,
        report.condition,
        uploaded_by,
    )
    return DetectionReportResponse.model_validate(loaded)


async def get_detections(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: str,
    course_id: uuid.UUID | None,
    condition_filter: str | None,
    page: int,
    limit: int,
) -> DetectionListResponse:
    filters: list = []

    if role == UserRole.worker.value:
        filters.append(DetectionReport.uploaded_by == user_id)
    elif not _admin_like(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list detection reports.",
        )

    if course_id is not None:
        filters.append(DetectionReport.course_id == course_id)

    if condition_filter:
        try:
            filters.append(DetectionReport.condition == DetectionCondition(condition_filter))
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid condition filter. Use: good, disease_found, or processing.",
            ) from err

    count_q = select(func.count(DetectionReport.id))
    if filters:
        count_q = count_q.where(*filters)
    total_result = await db.execute(count_q)
    total = int(total_result.scalar_one() or 0)

    q = (
        select(DetectionReport)
        .options(
            selectinload(DetectionReport.images),
            selectinload(DetectionReport.uploader),
            selectinload(DetectionReport.course),
        )
        .order_by(DetectionReport.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if filters:
        q = q.where(*filters)

    result = await db.execute(q)
    rows = result.scalars().all()

    return DetectionListResponse(
        detections=[DetectionReportResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


async def get_detection_by_id(
    db: AsyncSession,
    detection_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> DetectionReportResponse:
    report = await _get_detection_loaded(db, detection_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection report not found.",
        )

    if role == UserRole.worker.value and report.uploaded_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this detection report.",
        )
    if not _admin_like(role) and role != UserRole.worker.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this detection report.",
        )

    return DetectionReportResponse.model_validate(report)


async def update_detection_status(
    db: AsyncSession,
    detection_id: uuid.UUID,
    status_value: str,
    admin_user_id: uuid.UUID,
) -> DetectionReportResponse:
    if status_value not in ("approved", "flagged"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be approved or flagged.",
        )

    report = await _get_detection_loaded(db, detection_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection report not found.",
        )

    if report.status != DetectionReportStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed detection reports can be approved or flagged.",
        )

    report.status = (
        DetectionReportStatus.approved
        if status_value == "approved"
        else DetectionReportStatus.flagged
    )
    report.approved_by = admin_user_id
    report.reviewed_at = datetime.now(timezone.utc)

    await db.commit()

    loaded = await _get_detection_loaded(db, detection_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated detection report.",
        )
    logger.info(
        "Detection status updated id=%s status=%s admin_id=%s",
        detection_id,
        status_value,
        admin_user_id,
    )
    return DetectionReportResponse.model_validate(loaded)
