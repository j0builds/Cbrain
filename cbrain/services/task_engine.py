from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import Task, TimelineEvent


def _source_hash(source: str, identifier: str) -> str:
    return hashlib.sha256(f"{source}:{identifier}".encode()).hexdigest()


async def upsert_task(
    db: AsyncSession,
    title: str,
    description: str | None = None,
    source: str = "manual",
    source_id: str | None = None,
    urgency: str = "normal",
    assigned_to: uuid.UUID | None = None,
    due_date=None,
) -> tuple[Task, bool]:
    """Create or update a task, deduplicating by source + source_id.
    Returns (task, created) tuple."""
    created = False

    if source_id:
        sh = _source_hash(source, source_id)
        result = await db.execute(select(Task).where(Task.source_hash == sh))
        existing = result.scalar_one_or_none()
        if existing:
            # Update if content changed
            if existing.title != title or existing.description != description:
                existing.title = title
                existing.description = description
                existing.urgency = urgency
                if due_date:
                    existing.due_date = due_date
                await db.commit()
            return existing, False

    task = Task(
        title=title,
        description=description,
        source=source,
        source_id=source_id,
        source_hash=_source_hash(source, source_id or title),
        urgency=urgency,
        assigned_to=assigned_to,
        due_date=due_date,
    )
    db.add(task)
    created = True

    # Timeline event
    event = TimelineEvent(
        event_type="task_created",
        summary=f"Task created: {title}",
        source=source,
        source_ref=source_id,
        actor="task_engine",
    )
    db.add(event)

    await db.commit()
    await db.refresh(task)
    return task, created


async def get_open_tasks(db: AsyncSession, limit: int = 50) -> list[Task]:
    """Get open tasks sorted by priority (0 = highest)."""
    q = (
        select(Task)
        .where(Task.status.in_(["open", "in_progress", "blocked"]))
        .order_by(Task.priority.asc())
        .limit(limit)
    )
    result = await db.execute(q)
    return list(result.scalars().all())
