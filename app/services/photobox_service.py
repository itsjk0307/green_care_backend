from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import Date as SaDate

from app.models.golf_course import GolfCourse
from app.models.work_report import WorkReport
from app.schemas.photobox import (
    HolePhotoSummaryResponse,
    PhotoItemResponse,
    PhotoListResponse,
)
from app.utils.work_report_helpers import extract_hole_number


def _has_image_filter():
    return or_(
        WorkReport.before_image_path.isnot(None),
        WorkReport.after_image_path.isnot(None),
    )


async def _ensure_course_exists(db: AsyncSession, course_id: uuid.UUID) -> None:
    result = await db.execute(select(GolfCourse.id).where(GolfCourse.id == course_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )


def _report_to_photo_item(report: WorkReport) -> PhotoItemResponse:
    worker_name = report.worker.name if report.worker else "Unknown"
    hole = extract_hole_number(
        report.work_types,
        report.notes,
        report.zone_coordinates,
    )
    return PhotoItemResponse(
        id=report.id,
        course_id=report.course_id,
        work_types=report.work_types,
        notes=report.notes,
        before_image_path=report.before_image_path,
        after_image_path=report.after_image_path,
        hole_number=hole,
        worker_id=report.worker_id,
        worker_name=worker_name,
        created_at=report.created_at,
    )


async def list_photos(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    hole_number: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    work_type: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> PhotoListResponse:
    await _ensure_course_exists(db, course_id)

    if hole_number is not None and (hole_number < 1 or hole_number > 18):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hole_number must be between 1 and 18.",
        )

    per_page = min(max(per_page, 1), 50)
    page = max(page, 1)
    offset = (page - 1) * per_page

    base_filters = [
        WorkReport.course_id == course_id,
        _has_image_filter(),
    ]

    if from_date is not None:
        base_filters.append(cast(WorkReport.created_at, SaDate) >= from_date)
    if to_date is not None:
        base_filters.append(cast(WorkReport.created_at, SaDate) <= to_date)
    if work_type is not None:
        base_filters.append(WorkReport.work_types.contains([work_type]))

    stmt = (
        select(WorkReport)
        .where(*base_filters)
        .options(selectinload(WorkReport.worker))
        .order_by(WorkReport.created_at.desc())
    )

    if hole_number is not None:
        all_reports = (await db.execute(stmt)).scalars().all()
        filtered_reports = [
            report
            for report in all_reports
            if extract_hole_number(
                report.work_types,
                report.notes,
                report.zone_coordinates,
            )
            == hole_number
        ]
        total_count = len(filtered_reports)
        page_reports = filtered_reports[offset : offset + per_page]
        items = [_report_to_photo_item(report) for report in page_reports]
    else:
        count_stmt = select(func.count(WorkReport.id)).where(*base_filters)
        total_count = int((await db.execute(count_stmt)).scalar_one())
        result = await db.execute(stmt.offset(offset).limit(per_page))
        items = [_report_to_photo_item(report) for report in result.scalars().all()]

    return PhotoListResponse(
        items=items,
        total_count=total_count,
        page=page,
        per_page=per_page,
    )


async def get_photos_by_hole(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
) -> list[HolePhotoSummaryResponse]:
    await _ensure_course_exists(db, course_id)

    result = await db.execute(
        select(WorkReport)
        .where(
            WorkReport.course_id == course_id,
            _has_image_filter(),
        )
        .options(selectinload(WorkReport.worker))
        .order_by(WorkReport.created_at.desc())
    )
    reports = result.scalars().all()

    hole_data: dict[int, dict] = {
        hole: {
            "photo_count": 0,
            "last_photo_date": None,
            "latest_before_image": None,
            "latest_after_image": None,
        }
        for hole in range(1, 19)
    }

    for report in reports:
        hole = extract_hole_number(
            report.work_types,
            report.notes,
            report.zone_coordinates,
        )
        if hole is None:
            continue

        entry = hole_data[hole]
        entry["photo_count"] += 1
        report_date = report.created_at.date()

        if entry["last_photo_date"] is None or report_date > entry["last_photo_date"]:
            entry["last_photo_date"] = report_date
            entry["latest_before_image"] = report.before_image_path
            entry["latest_after_image"] = report.after_image_path
        elif report_date == entry["last_photo_date"]:
            if entry["latest_before_image"] is None:
                entry["latest_before_image"] = report.before_image_path
            if entry["latest_after_image"] is None:
                entry["latest_after_image"] = report.after_image_path

    summaries: list[HolePhotoSummaryResponse] = []
    for hole in range(1, 19):
        entry = hole_data[hole]
        summaries.append(
            HolePhotoSummaryResponse(
                hole_number=hole,
                photo_count=entry["photo_count"],
                last_photo_date=entry["last_photo_date"],
                latest_before_image=entry["latest_before_image"],
                latest_after_image=entry["latest_after_image"],
            )
        )

    return summaries
