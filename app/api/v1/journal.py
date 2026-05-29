from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.journal import (
    DailyJournalResponse,
    JournalExportRequest,
    MonthlyJournalResponse,
)
from app.services.journal_service import (
    export_journal_excel,
    get_daily_journal,
    get_monthly_journal,
)

journal_router = APIRouter(prefix="/journal", tags=["journal"])


@journal_router.get(
    "/daily",
    response_model=ApiResponse[DailyJournalResponse],
    status_code=status.HTTP_200_OK,
)
async def get_daily_journal_endpoint(
    course_id: uuid.UUID = Query(...),
    journal_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DailyJournalResponse]:
    _ = current_user
    data = await get_daily_journal(
        db=db,
        course_id=course_id,
        journal_date=journal_date,
    )
    return ApiResponse[DailyJournalResponse](
        success=True,
        message="Daily journal fetched successfully.",
        data=data,
    )


@journal_router.get(
    "/monthly",
    response_model=ApiResponse[MonthlyJournalResponse],
    status_code=status.HTTP_200_OK,
)
async def get_monthly_journal_endpoint(
    course_id: uuid.UUID = Query(...),
    month: str = Query(..., description="Month in YYYY-MM format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MonthlyJournalResponse]:
    _ = current_user
    data = await get_monthly_journal(db=db, course_id=course_id, month=month)
    return ApiResponse[MonthlyJournalResponse](
        success=True,
        message="Monthly journal fetched successfully.",
        data=data,
    )


@journal_router.post(
    "/export",
    status_code=status.HTTP_200_OK,
)
async def export_journal_endpoint(
    payload: JournalExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    _ = current_user

    if payload.format.lower() != "excel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only format='excel' is supported.",
        )

    buffer, filename = await export_journal_excel(
        db=db,
        course_id=payload.course_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
