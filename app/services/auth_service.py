from __future__ import annotations

import uuid
import traceback

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.diagnostics import fetch_runtime_database_info, mask_database_url
from app.db.session import engine
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserResponse


async def register_user(db: AsyncSession, user_data: UserCreate) -> UserResponse:
    try:
        existing_user = await db.execute(select(User).where(User.email == str(user_data.email)))
    except Exception as error:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
        ) from error
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    user = User(
        name=user_data.name,
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db_info = await fetch_runtime_database_info(engine)
    print(
        f"[REGISTER] Committed user id={user.id} email={user.email} "
        f"to database={db_info['database']!r} port={db_info['port']} "
        f"(DATABASE_URL={mask_database_url(settings.DATABASE_URL)})"
    )

    return UserResponse.model_validate(user)


async def login_user(db: AsyncSession, email: str, password: str) -> tuple[TokenResponse, User]:
    try:
        print("Step 1: Finding user")
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        print("Step 2: Verifying password")
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        print("Step 3: Creating token")
        payload = {
            "sub": str(user.id),
            "role": user.role.value,
        }
        token_response = TokenResponse(
            access_token=create_access_token(payload),
            refresh_token=create_refresh_token(payload),
            token_type="bearer",
        )
        return token_response, user
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    user_id_raw = payload.get("sub")

    if not isinstance(user_id_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from error

    try:
        result = await db.execute(select(User).where(User.id == user_id))
    except Exception as error:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
        ) from error
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for refresh token.",
        )

    payload = {
        "sub": str(user.id),
        "role": user.role.value,
    }
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        token_type="bearer",
    )

