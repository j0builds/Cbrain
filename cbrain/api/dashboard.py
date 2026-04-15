from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from cbrain.db.models import Question, Task, TimelineEvent
from cbrain.deps import DBSession

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db: DBSession):
    """Aggregated dashboard view: top tasks, pending questions, recent timeline."""

    tasks_q = (
        select(Task)
        .where(Task.status.in_(["open", "in_progress", "blocked"]))
        .order_by(Task.priority.asc())
        .limit(10)
    )
    tasks_result = await db.execute(tasks_q)
    top_tasks = tasks_result.scalars().all()

    questions_q = (
        select(Question)
        .where(Question.status == "pending")
        .order_by(Question.priority.asc())
        .limit(5)
    )
    questions_result = await db.execute(questions_q)
    pending_questions = questions_result.scalars().all()

    timeline_q = select(TimelineEvent).order_by(TimelineEvent.created_at.desc()).limit(20)
    timeline_result = await db.execute(timeline_q)
    recent_timeline = timeline_result.scalars().all()

    counts_q = select(Task.status, func.count(Task.id)).group_by(Task.status)
    counts_result = await db.execute(counts_q)
    task_counts = dict(counts_result.all())

    return {
        "tasks": [_task_dict(t) for t in top_tasks],
        "questions": [_question_dict(q) for q in pending_questions],
        "timeline": [_timeline_dict(e) for e in recent_timeline],
        "agents": [],
        "task_counts": task_counts,
    }


def _task_dict(t: Task) -> dict:
    return {
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
    }


def _question_dict(q: Question) -> dict:
    return {
        "id": str(q.id),
        "question_text": q.question_text,
        "context": q.context,
        "generated_by": q.generated_by,
        "priority": q.priority,
        "created_at": q.created_at.isoformat(),
    }


def _timeline_dict(e: TimelineEvent) -> dict:
    return {
        "id": str(e.id),
        "event_type": e.event_type,
        "summary": e.summary,
        "source": e.source,
        "actor": e.actor,
        "created_at": e.created_at.isoformat(),
    }
