from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import Question, Task, TeamMember
from cbrain.services.claude_client import ask_claude


async def generate_questions(
    db: AsyncSession,
    max_questions: int = 5,
) -> list[Question]:
    """Generate clarifying questions for the CEO based on context gaps."""
    # Get CEO
    result = await db.execute(select(TeamMember).where(TeamMember.is_ceo.is_(True)))
    ceo = result.scalar_one_or_none()
    if not ceo:
        return []

    # Get open tasks
    tasks_q = (
        select(Task)
        .where(Task.status.in_(["open", "in_progress", "blocked"]))
        .order_by(Task.priority.asc())
        .limit(20)
    )
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.scalars().all()

    if not tasks:
        return []

    # Get existing pending questions to avoid duplicates
    pending_q = select(Question).where(Question.status == "pending")
    pending_result = await db.execute(pending_q)
    pending = pending_result.scalars().all()
    existing_questions = [q.question_text for q in pending]

    tasks_text = "\n".join([
        f"- [{t.urgency}] {t.title} (status: {t.status}, blocker: {t.blocker or 'none'})"
        for t in tasks
    ])

    existing_text = "\n".join([f"- {q}" for q in existing_questions]) if existing_questions else "None"

    system = """You are the question generator for C-Brain, an enterprise brain for a startup CEO.
Generate targeted questions that help the CEO (Joseph) clarify priorities, unblock decisions,
and move the most important things forward.

Rules:
- Questions must be specific and actionable (not vague)
- Each question should help resolve a concrete ambiguity
- Avoid questions already pending
- Focus on: blocking decisions, stale tasks, ambiguous priorities, missing context
- Return JSON array of objects: [{question_text, context, priority}]
- priority: 0-100 (0 = most urgent)"""

    prompt = f"""Current open tasks:
{tasks_text}

Already pending questions:
{existing_text}

Generate up to {max_questions} new questions for Joseph. Return ONLY valid JSON array."""

    response = await ask_claude(prompt, system=system, max_tokens=2048)

    try:
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        questions_data = json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        return []

    created = []
    for qd in questions_data[:max_questions]:
        question = Question(
            question_text=qd.get("question_text", ""),
            context=qd.get("context", ""),
            directed_to=ceo.id,
            generated_by="agent:question_generator",
            priority=qd.get("priority", 50),
        )
        db.add(question)
        created.append(question)

    await db.commit()
    return created
