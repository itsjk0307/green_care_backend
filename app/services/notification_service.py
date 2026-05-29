from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

VALID_NOTIFICATION_TYPES = {
    "task_assigned",
    "issue_flagged",
    "issue_resolved",
    "issue_assigned",
    "ai_result_ready",
    "plan_published",
    "report_approved",
    "report_rejected",
}

VALID_REFERENCE_TYPES = {"work_report", "issue", "daily_plan", "drone_scan"}


def _validate_notification_type(notification_type: str) -> None:
    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification type: {notification_type}",
        )


def _validate_reference_type(reference_type: str | None) -> None:
    if reference_type is not None and reference_type not in VALID_REFERENCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reference type: {reference_type}",
        )


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    title_ko: str,
    title_en: str,
    body_ko: str | None = None,
    body_en: str | None = None,
    reference_id: uuid.UUID | None = None,
    reference_type: str | None = None,
) -> Notification:
    _validate_notification_type(notification_type)
    _validate_reference_type(reference_type)

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title_ko=title_ko,
        title_en=title_en,
        body_ko=body_ko,
        body_en=body_en,
        reference_id=reference_id,
        reference_type=reference_type,
        is_read=False,
    )
    db.add(notification)
    await db.flush()
    return notification


async def create_notifications_bulk(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    notification_type: str,
    title_ko: str,
    title_en: str,
    body_ko: str | None = None,
    body_en: str | None = None,
    reference_id: uuid.UUID | None = None,
    reference_type: str | None = None,
) -> int:
    if not user_ids:
        return 0

    _validate_notification_type(notification_type)
    _validate_reference_type(reference_type)

    unique_user_ids = list(dict.fromkeys(user_ids))
    notifications = [
        Notification(
            user_id=uid,
            type=notification_type,
            title_ko=title_ko,
            title_en=title_en,
            body_ko=body_ko,
            body_en=body_en,
            reference_id=reference_id,
            reference_type=reference_type,
            is_read=False,
        )
        for uid in unique_user_ids
    ]
    db.add_all(notifications)
    await db.flush()
    return len(notifications)


async def create_notifications_for_users(
    db: AsyncSession,
    *,
    user_ids: list[uuid.UUID],
    notification_type: str,
    title_ko: str,
    title_en: str,
    body_ko: str | None = None,
    body_en: str | None = None,
    reference_id: uuid.UUID | None = None,
    reference_type: str | None = None,
) -> int:
    """Backward-compatible alias used by daily plan publish."""
    return await create_notifications_bulk(
        db,
        user_ids,
        notification_type,
        title_ko,
        title_en,
        body_ko=body_ko,
        body_en=body_en,
        reference_id=reference_id,
        reference_type=reference_type,
    )


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse.model_validate(notification)


async def list_user_notifications(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> NotificationListResponse:
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * per_page

    count_stmt = (
        select(func.count(Notification.id))
        .where(Notification.user_id == user_id)
    )
    total_count = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    items = [_to_response(row) for row in result.scalars().all()]

    return NotificationListResponse(
        items=items,
        total_count=total_count,
        page=page,
        per_page=per_page,
    )


async def get_unread_count(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UnreadCountResponse:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    count = int((await db.execute(stmt)).scalar_one())
    return UnreadCountResponse(count=count)


async def mark_notification_read(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> NotificationResponse:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    if notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this notification.",
        )

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return _to_response(notification)


async def mark_all_notifications_read(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
        .returning(Notification.id)
    )
    updated_ids = result.scalars().all()
    await db.commit()
    return len(updated_ids)


async def delete_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    if notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this notification.",
        )

    await db.delete(notification)
    await db.commit()
