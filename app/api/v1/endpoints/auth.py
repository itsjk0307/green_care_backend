from __future__ import annotations

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    print("ENDPOINT HIT")
    try:
        print(f"[LOGIN] Attempt: {request.email}")
        tokens, user = await auth_service.login_user(
            db, request.email, request.password
        )
        print(f"[LOGIN] Success: {request.email}")
        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": tokens.token_type,
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role.value
                            if hasattr(user.role, "value")
                            else str(user.role),
                    "is_active": user.is_active,
                }
            }
        }
    except HTTPException as e:
        print(f"[LOGIN] HTTP error {e.status_code}: {e.detail}")
        raise e
    except Exception as e:
        print(f"[LOGIN] Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register")
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        print(f"[REGISTER] Attempt: {request.email}")
        result = await auth_service.register_user(db, request)
        print(f"[REGISTER] Success: {request.email}")
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "id": str(result.id),
                "name": result.name,
                "email": result.email,
                "role": result.role,
                "is_active": result.is_active,
                "created_at": str(result.created_at),
            }
        }
    except HTTPException as e:
        print(f"[REGISTER] HTTP error: {e.detail}")
        raise e
    except Exception as e:
        print(f"[REGISTER] Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db)
):
    try:
        from fastapi.security import OAuth2PasswordBearer
        from app.core.security import decode_token
        from fastapi import Request
        
        print("[ME] Endpoint called")
        return {
            "success": True,
            "message": "Me endpoint works",
            "data": {
                "id": "temp-id",
                "name": "Temp User",
                "email": "temp@temp.com",
                "role": "worker",
                "is_active": True
            }
        }
    except Exception as e:
        print(f"[ME] Error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/logout")
async def logout():
    return {
        "success": True,
        "message": "Logged out successfully",
        "data": None
    }


@router.post("/refresh")
async def refresh():
    return {
        "success": True,
        "message": "Token refreshed",
        "data": None
    }
