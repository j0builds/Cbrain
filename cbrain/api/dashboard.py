from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from cbrain.db.models import AgentRun, Question, Task, TimelineEvent
from cbrain.deps import DBSession

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db: DBSession):
    """Aggregated dashboard view: top tasks, pending questions, recent timeline, agent status."""

    # Top 10 open tasks by priority
    tasks_q = (
        select(Task)
        .where(Task.status.in_(["open", "in_progress", "blocked"]))
        .order_by(Task.priority.asc())
        .limit(10)
    )
    tasks_result = await db.execute(tasks_q)
    top_tasks = tasks_result.scalars().all()

    # Pending questions
    questions_q = (
        select(Question)
        .where(Question.status == "pending")
        .order_by(Question.priority.asc())
        .limit(5)
    )
    questions_result = await db.execute(questions_q)
    pending_questions = questions_result.scalars().all()

    # Recent timeline (last 20 events)
    timeline_q = select(TimelineEvent).order_by(TimelineEvent.created_at.desc()).limit(20)
    timeline_result = await db.execute(timeline_q)
    recent_timeline = timeline_result.scalars().all()

    # Agent status (latest run per agent)
    agent_q = (
        select(AgentRun)
        .distinct(AgentRun.agent_name)
        .order_by(AgentRun.agent_name, AgentRun.started_at.desc())
    )
    agent_result = await db.execute(agent_q)
    agent_status = agent_result.scalars().all()

    # Task counts by status
    counts_q = select(Task.status, func.count(Task.id)).group_by(Task.status)
    counts_result = await db.execute(counts_q)
    task_counts = dict(counts_result.all())

    return {
        "tasks": [_task_dict(t) for t in top_tasks],
        "questions": [_question_dict(q) for q in pending_questions],
        "timeline": [_timeline_dict(e) for e in recent_timeline],
        "agents": [_agent_dict(a) for a in agent_status],
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


def _agent_dict(a: AgentRun) -> dict:
    return {
        "agent_name": a.agent_name,
        "status": a.status,
        "started_at": a.started_at.isoformat(),
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "summary": a.summary,
    }
