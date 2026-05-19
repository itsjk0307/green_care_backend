from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=ApiResponse[list[UserResponse]])
async def list_users(
    role: UserRole | None = Query(None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[UserResponse]]:
    query = select(User).where(User.is_active.is_(True))
    if role is not None:
        query = query.where(User.role == role)
    query = query.order_by(User.name)

    result = await db.execute(query)
    users = result.scalars().all()
    return ApiResponse[list[UserResponse]](
        success=True,
        message="Users fetched successfully.",
        data=[UserResponse.model_validate(u) for u in users],
    )
