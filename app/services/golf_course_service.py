from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.golf_course import GolfCourse
from app.schemas.golf_course import GolfCourseCreate, GolfCourseResponse, GolfCourseUpdate

logger = logging.getLogger(__name__)


async def create_course(db: AsyncSession, data: GolfCourseCreate) -> GolfCourseResponse:
    course = GolfCourse(
        name=data.name,
        name_ko=data.name_ko,
        address=data.address,
        address_ko=data.address_ko,
        total_area_sqm=data.total_area_sqm,
        map_image_path=data.map_image_path,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    logger.info("Created golf course id=%s name=%s", course.id, course.name)
    return GolfCourseResponse.model_validate(course)


async def get_all_courses(db: AsyncSession) -> list[GolfCourseResponse]:
    result = await db.execute(select(GolfCourse).order_by(GolfCourse.created_at))
    courses = result.scalars().all()
    return [GolfCourseResponse.model_validate(c) for c in courses]


async def get_course_by_id(db: AsyncSession, course_id: uuid.UUID) -> GolfCourseResponse:
    result = await db.execute(select(GolfCourse).where(GolfCourse.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )
    return GolfCourseResponse.model_validate(course)


async def get_course_model_by_id(db: AsyncSession, course_id: uuid.UUID) -> GolfCourse | None:
    result = await db.execute(select(GolfCourse).where(GolfCourse.id == course_id))
    return result.scalar_one_or_none()


async def update_course(
    db: AsyncSession,
    course_id: uuid.UUID,
    data: GolfCourseUpdate,
) -> GolfCourseResponse:
    result = await db.execute(select(GolfCourse).where(GolfCourse.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found.",
        )
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    logger.info("Updated golf course id=%s fields=%s", course.id, list(payload.keys()))
    return GolfCourseResponse.model_validate(course)
