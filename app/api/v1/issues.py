from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.issue import (
    IssueCreate,
    IssueMapResponse,
    IssueResponse,
    IssueUpdateRequest,
)
from app.services.issue_service import (
    create_issue,
    delete_issue,
    get_issue,
    list_issues_for_map,
    update_issue,
)

issues_router = APIRouter(prefix="/issues", tags=["issues"])


@issues_router.post(
    "/",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_issue_endpoint(
    course_id: uuid.UUID = Form(...),
    issue_type: str = Form(...),
    priority: str = Form(default="medium"),
    title: str = Form(...),
    description: str | None = Form(default=None),
    pin_x: float = Form(...),
    pin_y: float = Form(...),
    hole_number: int | None = Form(default=None),
    assigned_to: uuid.UUID | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IssueResponse]:
    try:
        payload = IssueCreate.model_validate(
            {
                "course_id": course_id,
                "issue_type": issue_type,
                "priority": priority,
                "title": title,
                "description": description,
                "pin_x": pin_x,
                "pin_y": pin_y,
                "hole_number": hole_number,
                "assigned_to": assigned_to,
            }
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    data = await create_issue(
        db=db,
        reported_by=current_user.id,
        payload=payload,
        image=image,
    )
    return ApiResponse[IssueResponse](
        success=True,
        message="Issue created successfully.",
        data=data,
    )


@issues_router.get(
    "/",
    response_model=ApiResponse[list[IssueMapResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_issues_endpoint(
    course_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    issue_type: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    hole_number: int | None = Query(default=None, ge=1, le=18),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[IssueMapResponse]]:
    _ = current_user
    data = await list_issues_for_map(
        db=db,
        course_id=course_id,
        status_filter=status_filter,
        issue_type=issue_type,
        priority=priority,
        hole_number=hole_number,
    )
    return ApiResponse[list[IssueMapResponse]](
        success=True,
        message="Issues fetched successfully.",
        data=data,
    )


@issues_router.get(
    "/{issue_id}",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_200_OK,
)
async def get_issue_endpoint(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IssueResponse]:
    _ = current_user
    data = await get_issue(db=db, issue_id=issue_id)
    return ApiResponse[IssueResponse](
        success=True,
        message="Issue fetched successfully.",
        data=data,
    )


@issues_router.patch(
    "/{issue_id}",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_200_OK,
)
async def update_issue_endpoint(
    issue_id: uuid.UUID,
    payload: IssueUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IssueResponse]:
    _ = current_user
    data = await update_issue(db=db, issue_id=issue_id, payload=payload)
    return ApiResponse[IssueResponse](
        success=True,
        message="Issue updated successfully.",
        data=data,
    )


@issues_router.delete(
    "/{issue_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_issue_endpoint(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await delete_issue(db=db, issue_id=issue_id, current_user=current_user)
    return {
        "success": True,
        "message": "삭제되었습니다",
        "data": None,
    }
