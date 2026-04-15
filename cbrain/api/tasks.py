from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cbrain.db.models import Task
from cbrain.deps import DBSession

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    urgency: str = "normal"
    source: str = "manual"
    due_date: datetime | None = None
    assigned_to: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    priority_reason: str | None = None
    urgency: str | None = None
    blocker: str | None = None
    assigned_to: uuid.UUID | None = None
    due_date: datetime | None = None


@router.get("")
async def list_tasks(
    db: DBSession,
    status: str | None = None,
    urgency: str | None = None,
    assigned_to: uuid.UUID | None = None,
    limit: int = 50,
):
    q = select(Task).order_by(Task.priority.asc())

    if status:
        q = q.where(Task.status == status)
    else:
        q = q.where(Task.status.in_(["open", "in_progress", "blocked"]))

    if urgency:
        q = q.where(Task.urgency == urgency)
    if assigned_to:
        q = q.where(Task.assigned_to == assigned_to)

    q = q.limit(limit)
    result = await db.execute(q)
    tasks = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "priority_reason": t.priority_reason,
            "urgency": t.urgency,
            "status": t.status,
            "blocker": t.blocker,
            "source": t.source,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        for t in tasks
    ]


@router.get("/{task_id}")
async def get_task(task_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "priority_reason": task.priority_reason,
        "urgency": task.urgency,
        "status": task.status,
        "blocker": task.blocker,
        "source": task.source,
        "source_id": task.source_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "related_context_ids": [str(c) for c in (task.related_context_ids or [])],
        "suggested_skill_ids": [str(s) for s in (task.suggested_skill_ids or [])],
    }


@router.post("", status_code=201)
async def create_task(body: TaskCreate, db: DBSession):
    task = Task(
        title=body.title,
        description=body.description,
        urgency=body.urgency,
        source=body.source,
        due_date=body.due_date,
        assigned_to=body.assigned_to,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": str(task.id), "title": task.title}


@router.patch("/{task_id}")
async def update_task(task_id: uuid.UUID, body: TaskUpdate, db: DBSession):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    if body.status == "done" and not task.completed_at:
        task.completed_at = datetime.now()

    await db.commit()
    return {"id": str(task.id), "status": task.status}
