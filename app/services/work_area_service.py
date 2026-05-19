from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_area import WorkArea
from app.schemas.work_area import WorkAreaResponse


async def list_work_areas(
    db: AsyncSession,
    course_id: uuid.UUID | None = None,
) -> list[WorkAreaResponse]:
    q = select(WorkArea).order_by(WorkArea.created_at.desc())
    if course_id is not None:
        q = q.where(WorkArea.course_id == course_id)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [WorkAreaResponse.model_validate(r) for r in rows]
