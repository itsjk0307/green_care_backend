from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)
from app.services.notification_service import (
    delete_notification,
    get_unread_count,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get(
    "/",
    response_model=ApiResponse[NotificationListResponse],
    status_code=status.HTTP_200_OK,
)
async def list_notifications_endpoint(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NotificationListResponse]:
    data = await list_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )
    return ApiResponse[NotificationListResponse](
        success=True,
        message="Notifications fetched successfully.",
        data=data,
    )


@notifications_router.get(
    "/unread-count",
    response_model=ApiResponse[UnreadCountResponse],
    status_code=status.HTTP_200_OK,
)
async def get_unread_count_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[UnreadCountResponse]:
    data = await get_unread_count(db=db, user_id=current_user.id)
    return ApiResponse[UnreadCountResponse](
        success=True,
        message="",
        data=data,
    )


@notifications_router.patch(
    "/read-all",
    response_model=ApiResponse[ReadAllResponse],
    status_code=status.HTTP_200_OK,
)
async def mark_all_read_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ReadAllResponse]:
    count_updated = await mark_all_notifications_read(db=db, user_id=current_user.id)
    return ApiResponse[ReadAllResponse](
        success=True,
        message="All notifications marked as read.",
        data=ReadAllResponse(count_updated=count_updated),
    )


@notifications_router.patch(
    "/{notification_id}/read",
    response_model=ApiResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
)
async def mark_notification_read_endpoint(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NotificationResponse]:
    data = await mark_notification_read(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return ApiResponse[NotificationResponse](
        success=True,
        message="Notification marked as read.",
        data=data,
    )


@notifications_router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_notification_endpoint(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await delete_notification(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return {
        "success": True,
        "message": "삭제되었습니다",
        "data": None,
    }
