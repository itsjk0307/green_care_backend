from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.golf_course import GolfCourse
from app.models.issue import Issue
from app.models.user import User, UserRole
from app.schemas.issue import (
    IssueCreate,
    IssueMapResponse,
    IssueResponse,
    IssueUpdateRequest,
)
from app.services.notification_service import create_notification
from app.services.storage_service import delete_storage_file, save_issue_image

_VALID_ISSUE_TYPES = {"disease", "equipment", "irrigation", "turf_damage", "other"}
_VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_VALID_STATUSES = {"open", "in_progress", "resolved"}

_PRIORITY_SORT = case(
    (Issue.priority == "critical", 0),
    (Issue.priority == "high", 1),
    (Issue.priority == "medium", 2),
    else_=3,
)


async def _get_course_or_404(db: AsyncSession, course_id: uuid.UUID) -> GolfCourse:
    result = await db.execute(select(GolfCourse.id).where(GolfCourse.id == course_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )
    return user


async def _get_issue_loaded(db: AsyncSession, issue_id: uuid.UUID) -> Issue | None:
    result = await db.execute(
        select(Issue)
        .where(Issue.id == issue_id)
        .options(
            selectinload(Issue.reporter),
            selectinload(Issue.assignee),
            selectinload(Issue.course),
        )
    )
    return result.scalar_one_or_none()


def _to_issue_response(issue: Issue) -> IssueResponse:
    reporter_name = issue.reporter.name if issue.reporter else "Unknown"
    assignee_name = issue.assignee.name if issue.assignee else None
    return IssueResponse(
        id=issue.id,
        course_id=issue.course_id,
        issue_type=issue.issue_type,
        priority=issue.priority,
        title=issue.title,
        description=issue.description,
        image_path=issue.image_path,
        pin_x=issue.pin_x,
        pin_y=issue.pin_y,
        hole_number=issue.hole_number,
        status=issue.status,
        resolved_at=issue.resolved_at,
        reported_by=issue.reported_by,
        reporter_name=reporter_name,
        assigned_to=issue.assigned_to,
        assignee_name=assignee_name,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


def _to_issue_map_response(issue: Issue) -> IssueMapResponse:
    reporter_name = issue.reporter.name if issue.reporter else "Unknown"
    return IssueMapResponse(
        id=issue.id,
        issue_type=issue.issue_type,
        priority=issue.priority,
        title=issue.title,
        pin_x=issue.pin_x,
        pin_y=issue.pin_y,
        status=issue.status,
        hole_number=issue.hole_number,
        reporter_name=reporter_name,
        created_at=issue.created_at,
    )


async def _notify_issue_assigned(
    db: AsyncSession,
    *,
    assignee_id: uuid.UUID,
    issue: Issue,
) -> None:
    await create_notification(
        db,
        user_id=assignee_id,
        notification_type="issue_assigned",
        title_ko=f"새 이슈가 배정되었습니다: {issue.title}",
        title_en=f"New issue assigned: {issue.title}",
        body_ko=f"우선순위: {issue.priority}",
        body_en=f"Priority: {issue.priority}",
        reference_id=issue.id,
        reference_type="issue",
    )


async def create_issue(
    db: AsyncSession,
    *,
    reported_by: uuid.UUID,
    payload: IssueCreate,
    image: UploadFile | None = None,
) -> IssueResponse:
    await _get_course_or_404(db, payload.course_id)

    if payload.assigned_to is not None:
        await _get_user_or_404(db, payload.assigned_to)

    image_path: str | None = None
    if image is not None and image.filename and image.filename.strip():
        image_path = await save_issue_image(image)

    issue = Issue(
        course_id=payload.course_id,
        reported_by=reported_by,
        assigned_to=payload.assigned_to,
        issue_type=payload.issue_type,
        priority=payload.priority,
        title=payload.title,
        description=payload.description,
        image_path=image_path,
        pin_x=payload.pin_x,
        pin_y=payload.pin_y,
        hole_number=payload.hole_number,
        status="open",
    )
    db.add(issue)
    await db.flush()

    if payload.assigned_to is not None:
        await _notify_issue_assigned(db, assignee_id=payload.assigned_to, issue=issue)

    await db.commit()

    loaded = await _get_issue_loaded(db, issue.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created issue.",
        )
    return _to_issue_response(loaded)


async def list_issues_for_map(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    status_filter: str | None = None,
    issue_type: str | None = None,
    priority: str | None = None,
    hole_number: int | None = None,
) -> list[IssueMapResponse]:
    await _get_course_or_404(db, course_id)

    if status_filter is not None and status_filter not in _VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(_VALID_STATUSES)}",
        )
    if issue_type is not None and issue_type not in _VALID_ISSUE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid issue_type. Allowed: {sorted(_VALID_ISSUE_TYPES)}",
        )
    if priority is not None and priority not in _VALID_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Allowed: {sorted(_VALID_PRIORITIES)}",
        )
    if hole_number is not None and (hole_number < 1 or hole_number > 18):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hole_number must be between 1 and 18.",
        )

    stmt = (
        select(Issue)
        .where(Issue.course_id == course_id)
        .options(selectinload(Issue.reporter))
        .order_by(_PRIORITY_SORT.asc(), Issue.created_at.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(Issue.status == status_filter)
    if issue_type is not None:
        stmt = stmt.where(Issue.issue_type == issue_type)
    if priority is not None:
        stmt = stmt.where(Issue.priority == priority)
    if hole_number is not None:
        stmt = stmt.where(Issue.hole_number == hole_number)

    result = await db.execute(stmt)
    issues = result.scalars().all()
    return [_to_issue_map_response(issue) for issue in issues]


async def get_issue(
    db: AsyncSession,
    issue_id: uuid.UUID,
) -> IssueResponse:
    issue = await _get_issue_loaded(db, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found.",
        )
    return _to_issue_response(issue)


async def update_issue(
    db: AsyncSession,
    issue_id: uuid.UUID,
    payload: IssueUpdateRequest,
) -> IssueResponse:
    issue = await _get_issue_loaded(db, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update.",
        )

    previous_assignee = issue.assigned_to

    if "status" in updates:
        status_value = updates["status"]
        if status_value not in _VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {sorted(_VALID_STATUSES)}",
            )
        issue.status = status_value
        if status_value == "resolved":
            issue.resolved_at = datetime.now(timezone.utc)
        else:
            issue.resolved_at = None

    if "priority" in updates:
        priority_value = updates["priority"]
        if priority_value not in _VALID_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Allowed: {sorted(_VALID_PRIORITIES)}",
            )
        issue.priority = priority_value

    if "title" in updates:
        issue.title = updates["title"]

    if "description" in updates:
        issue.description = updates["description"]

    if "assigned_to" in updates:
        new_assignee = updates["assigned_to"]
        if new_assignee is not None:
            await _get_user_or_404(db, new_assignee)
        issue.assigned_to = new_assignee

    issue.updated_at = datetime.now(timezone.utc)

    if issue.assigned_to is not None and issue.assigned_to != previous_assignee:
        await _notify_issue_assigned(db, assignee_id=issue.assigned_to, issue=issue)

    await db.commit()

    loaded = await _get_issue_loaded(db, issue_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated issue.",
        )
    return _to_issue_response(loaded)


async def delete_issue(
    db: AsyncSession,
    issue_id: uuid.UUID,
    current_user: User,
) -> None:
    issue = await _get_issue_loaded(db, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found.",
        )

    is_reporter = issue.reported_by == current_user.id
    is_privileged = current_user.role in {UserRole.admin, UserRole.manager}

    if not is_reporter and not is_privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporter or an admin/manager can delete this issue.",
        )

    image_path = issue.image_path
    await db.delete(issue)
    await db.commit()

    if image_path:
        await delete_storage_file(image_path)
