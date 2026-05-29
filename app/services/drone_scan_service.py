from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_work_plan import DailyWorkPlan, DailyWorkerAttendance
from app.models.drone_scan import DroneScan, ScanResult
from app.models.golf_course import GolfCourse
from app.models.user import User
from app.models.work_report import WorkReport
from app.schemas.drone_scan import (
    DroneScanDetailResponse,
    DroneScanResponse,
    ScanResultResponse,
)
from app.services.drone_ai_service import get_fixed_mock_scan_results
from app.services.notification_service import create_notifications_bulk


async def _get_active_course_worker_ids(
    db: AsyncSession,
    course_id: uuid.UUID,
) -> list[uuid.UUID]:
    worker_ids: set[uuid.UUID] = set()

    report_result = await db.execute(
        select(WorkReport.worker_id).where(WorkReport.course_id == course_id).distinct()
    )
    worker_ids.update(row[0] for row in report_result.all())

    attendance_result = await db.execute(
        select(DailyWorkerAttendance.worker_id)
        .join(DailyWorkPlan, DailyWorkPlan.id == DailyWorkerAttendance.plan_id)
        .where(DailyWorkPlan.course_id == course_id)
        .distinct()
    )
    worker_ids.update(row[0] for row in attendance_result.all())

    if not worker_ids:
        active_workers = await db.execute(
            select(User.id).where(User.is_active.is_(True))
        )
        worker_ids.update(row[0] for row in active_workers.all())

    return list(worker_ids)


async def _get_course_or_404(db: AsyncSession, course_id: uuid.UUID) -> GolfCourse:
    result = await db.execute(select(GolfCourse).where(GolfCourse.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )
    return course


async def _get_scan_loaded(
    db: AsyncSession,
    scan_id: uuid.UUID,
) -> DroneScan | None:
    result = await db.execute(
        select(DroneScan)
        .where(DroneScan.id == scan_id)
        .options(
            selectinload(DroneScan.results),
            selectinload(DroneScan.course),
            selectinload(DroneScan.uploader),
        )
    )
    return result.scalar_one_or_none()


def _to_scan_response(scan: DroneScan) -> DroneScanResponse:
    result_count = len(scan.results) if scan.results is not None else 0
    return DroneScanResponse(
        id=scan.id,
        course_id=scan.course_id,
        uploaded_by=scan.uploaded_by,
        scan_date=scan.scan_date,
        image_path=scan.image_path,
        image_width=scan.image_width,
        image_height=scan.image_height,
        status=scan.status,
        notes=scan.notes,
        created_at=scan.created_at,
        result_count=result_count,
    )


def _to_scan_detail(scan: DroneScan) -> DroneScanDetailResponse:
    result_count = len(scan.results) if scan.results is not None else 0
    return DroneScanDetailResponse(
        id=scan.id,
        course_id=scan.course_id,
        uploaded_by=scan.uploaded_by,
        scan_date=scan.scan_date,
        image_path=scan.image_path,
        image_width=scan.image_width,
        image_height=scan.image_height,
        status=scan.status,
        notes=scan.notes,
        created_at=scan.created_at,
        result_count=result_count,
        results=[ScanResultResponse.model_validate(r) for r in scan.results],
    )


async def create_drone_scan(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    scan_date: date,
    image_path: str,
    image_width: int,
    image_height: int,
    notes: str | None,
) -> DroneScanResponse:
    await _get_course_or_404(db, course_id)

    scan = DroneScan(
        course_id=course_id,
        uploaded_by=uploaded_by,
        scan_date=scan_date,
        image_path=image_path,
        image_width=image_width,
        image_height=image_height,
        status="uploaded",
        notes=notes,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan, attribute_names=["results"])
    return _to_scan_response(scan)


async def list_drone_scans(
    db: AsyncSession,
    *,
    course_id: uuid.UUID | None = None,
) -> list[DroneScanResponse]:
    stmt = (
        select(DroneScan)
        .options(selectinload(DroneScan.results))
        .order_by(DroneScan.created_at.desc())
    )
    if course_id is not None:
        stmt = stmt.where(DroneScan.course_id == course_id)

    result = await db.execute(stmt)
    scans = result.scalars().all()
    return [_to_scan_response(scan) for scan in scans]


async def get_drone_scan_detail(
    db: AsyncSession,
    scan_id: uuid.UUID,
) -> DroneScanDetailResponse:
    scan = await _get_scan_loaded(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drone scan not found.",
        )
    return _to_scan_detail(scan)


async def get_latest_completed_scan(
    db: AsyncSession,
    course_id: uuid.UUID,
) -> DroneScanDetailResponse:
    await _get_course_or_404(db, course_id)

    result = await db.execute(
        select(DroneScan)
        .where(
            DroneScan.course_id == course_id,
            DroneScan.status == "completed",
        )
        .options(selectinload(DroneScan.results))
        .order_by(DroneScan.created_at.desc())
        .limit(1)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed drone scan found for this course.",
        )
    return _to_scan_detail(scan)


async def analyze_drone_scan(
    db: AsyncSession,
    scan_id: uuid.UUID,
) -> DroneScanDetailResponse:
    scan = await _get_scan_loaded(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drone scan not found.",
        )

    if scan.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only scans with status 'uploaded' can be analyzed. Current status: {scan.status}",
        )

    scan.status = "processing"
    await db.commit()
    await db.refresh(scan)

    try:
        mock_results = get_fixed_mock_scan_results()

        for existing in list(scan.results):
            await db.delete(existing)
        await db.flush()

        for item in mock_results:
            db.add(
                ScanResult(
                    scan_id=scan.id,
                    hole_number=item["hole_number"],
                    disease_type=item["disease_type"],
                    confidence=item["confidence"],
                    severity=item.get("severity"),
                    affected_area_pct=item.get("affected_area_pct"),
                    bbox_x=item.get("bbox_x"),
                    bbox_y=item.get("bbox_y"),
                    bbox_width=item.get("bbox_width"),
                    bbox_height=item.get("bbox_height"),
                    recommendation_ko=item.get("recommendation_ko"),
                    recommendation_en=item.get("recommendation_en"),
                )
            )

        scan.status = "completed"
        await db.flush()

        worker_ids = await _get_active_course_worker_ids(db, scan.course_id)
        if worker_ids:
            await create_notifications_bulk(
                db,
                worker_ids,
                notification_type="ai_result_ready",
                title_ko="드론 스캔 AI 분석이 완료되었습니다",
                title_en="Drone scan AI analysis is ready",
                body_ko=f"스캔 날짜 {scan.scan_date} 분석 결과를 확인하세요.",
                body_en=f"View analysis results for scan date {scan.scan_date}.",
                reference_id=scan.id,
                reference_type="drone_scan",
            )

        await db.commit()
    except HTTPException:
        raise
    except Exception as error:
        scan.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drone scan analysis failed: {error}",
        ) from error

    refreshed = await _get_scan_loaded(db, scan_id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Drone scan missing after analysis.",
        )
    return _to_scan_detail(refreshed)


async def get_scan_results_for_course(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    hole: int | None = None,
) -> list[ScanResultResponse]:
    if hole is not None and (hole < 1 or hole > 18):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hole must be between 1 and 18.",
        )

    await _get_course_or_404(db, course_id)

    latest_scan_id = await db.scalar(
        select(DroneScan.id)
        .where(
            DroneScan.course_id == course_id,
            DroneScan.status == "completed",
        )
        .order_by(DroneScan.created_at.desc())
        .limit(1)
    )
    if latest_scan_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed drone scan found for this course.",
        )

    stmt = select(ScanResult).where(ScanResult.scan_id == latest_scan_id)
    if hole is not None:
        stmt = stmt.where(ScanResult.hole_number == hole)

    stmt = stmt.order_by(ScanResult.hole_number.asc())
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        if hole is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scan results for hole {hole} on the latest completed scan.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scan results found on the latest completed scan.",
        )

    return [ScanResultResponse.model_validate(row) for row in rows]
