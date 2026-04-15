"""Execute skills by querying the brain's context store and assembling structured documents.
Works without LLM credits — pure data assembly."""
from __future__ import annotations

import json
import time
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import ContextEntry, Question, Skill, SkillExecution, Task, TeamMember, TimelineEvent
from cbrain.services.context_store import hybrid_search


async def execute_skill(
    db: AsyncSession,
    skill: Skill,
    input_data: dict,
    triggered_by: str = "user",
) -> SkillExecution:
    """Execute a skill using brain data. No LLM required."""
    execution = SkillExecution(
        skill_id=skill.id,
        input_data=input_data,
        status="running",
        triggered_by=triggered_by,
    )
    db.add(execution)
    await db.flush()

    start = time.monotonic()
    try:
        # Route to the right handler
        handlers = {
            "prioritize_tasks": _run_prioritize_tasks,
            "team_pulse": _run_team_pulse,
            "decision_brief": _run_decision_brief,
            "summarize_context": _run_summarize_context,
            "analyze_blocker": _run_analyze_blocker,
            "draft_message": _run_draft_message,
        }

        handler = handlers.get(skill.name)
        if handler:
            output = await handler(db, input_data)
        else:
            output = f"Skill '{skill.name}' has no handler yet."

        execution.output_text = output
        execution.status = "completed"
        execution.duration_ms = int((time.monotonic() - start) * 1000)

        skill.execution_count += 1
        skill.last_executed_at = datetime.now()

    except Exception as e:
        execution.status = "failed"
        execution.error_message = str(e)
        execution.duration_ms = int((time.monotonic() - start) * 1000)

    await db.commit()
    await db.refresh(execution)
    return execution


async def _run_prioritize_tasks(db: AsyncSession, input_data: dict) -> str:
    """Analyze open tasks and produce a priority ranking from brain data."""
    q = (
        select(Task)
        .where(Task.status.in_(["open", "in_progress", "blocked"]))
        .order_by(Task.priority.asc())
        .limit(30)
    )
    result = await db.execute(q)
    tasks = result.scalars().all()

    if not tasks:
        return "## Task Cortex: No Open Signals\n\nNo tasks found. Sync from Notion or Jopedia to populate."

    # Sort: blocked first, then by urgency, then by age
    urgency_rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}

    def sort_key(t: Task):
        blocked = 0 if t.status == "blocked" else 1
        urg = urgency_rank.get(t.urgency, 2)
        age = (datetime.now() - t.created_at.replace(tzinfo=None)).days if t.created_at else 0
        return (blocked, urg, -age)

    sorted_tasks = sorted(tasks, key=sort_key)

    lines = ["## Task Cortex: Priority Analysis", ""]

    # Blocked tasks — top priority
    blocked = [t for t in sorted_tasks if t.status == "blocked"]
    if blocked:
        lines.append("### BLOCKED — Requires immediate action")
        for t in blocked:
            lines.append(f"- **{t.title}** — {t.blocker or 'No blocker specified'}")
        lines.append("")

    # Critical/High urgency
    urgent = [t for t in sorted_tasks if t.urgency in ("critical", "high") and t.status != "blocked"]
    if urgent:
        lines.append("### HIGH PRIORITY")
        for t in urgent:
            age = (datetime.now() - t.created_at.replace(tzinfo=None)).days if t.created_at else 0
            lines.append(f"- **{t.title}** [{t.urgency.upper()}] — {age}d old, source: {t.source}")
        lines.append("")

    # Normal
    normal = [t for t in sorted_tasks if t.urgency == "normal" and t.status != "blocked"]
    if normal:
        lines.append("### NORMAL PRIORITY")
        for t in normal[:10]:
            lines.append(f"- {t.title} — {t.source}")
        if len(normal) > 10:
            lines.append(f"- ... and {len(normal) - 10} more")
        lines.append("")

    # Stats
    lines.append("---")
    lines.append(f"**Total open:** {len(tasks)} | **Blocked:** {len(blocked)} | **Urgent:** {len(urgent)}")

    return "\n".join(lines)


async def _run_team_pulse(db: AsyncSession, input_data: dict) -> str:
    """Show what the brain knows about each team member."""
    result = await db.execute(select(TeamMember).order_by(TeamMember.name))
    members = result.scalars().all()

    lines = ["## Team Pulse Check", ""]

    for member in members:
        lines.append(f"### {member.name} — {member.role}")

        # Search context for this person
        results = await hybrid_search(db, member.name, limit=5)
        if results:
            lines.append(f"**Brain entries:** {len(results)} relevant")
            for r in results[:3]:
                lines.append(f"- [{r['entry_type']}] {r['title']}: {r['body'][:120]}...")
        else:
            lines.append("**Brain entries:** No context found")

        # Count their tasks
        tasks_q = select(func.count(Task.id)).where(
            Task.status.in_(["open", "in_progress", "blocked"])
        )
        # Note: assigned_to may not be set for most tasks in MVP
        task_count = await db.execute(
            select(func.count(Task.id)).where(Task.status.in_(["open", "in_progress"]))
        )

        lines.append("")

    return "\n".join(lines)


async def _run_decision_brief(db: AsyncSession, input_data: dict) -> str:
    """Search brain for context on a decision topic and present structured brief."""
    topic = input_data.get("topic") or input_data.get("focus_area") or "general strategy"

    results = await hybrid_search(db, topic, limit=10)

    lines = ["## Decision Brief", f"### Topic: {topic}", ""]

    if not results:
        lines.append(f"No brain entries found for \"{topic}\". Try syncing more data or using a broader search term.")
        return "\n".join(lines)

    lines.append("### Relevant Context")
    for r in results:
        tier_marker = {"critical": "!!!", "high": "!!", "medium": "!", "low": ""}.get(r["importance_tier"], "")
        lines.append(f"**{r['title']}** {tier_marker} ({r['entry_type']}, score: {r['score']:.3f})")
        # Show first 200 chars of body
        body_preview = r["body"][:200].replace("\n", " ")
        lines.append(f"> {body_preview}...")
        if r["tags"]:
            lines.append(f"Tags: {', '.join(r['tags'][:5])}")
        lines.append("")

    lines.append("---")
    lines.append(f"**{len(results)} entries found** — review above context to inform your decision.")

    return "\n".join(lines)


async def _run_summarize_context(db: AsyncSession, input_data: dict) -> str:
    """Search brain and summarize all context on a topic."""
    topic = input_data.get("topic") or input_data.get("focus_area") or ""

    if not topic:
        # Show brain stats instead
        total = await db.execute(select(func.count(ContextEntry.id)))
        total_count = total.scalar() or 0

        by_type = await db.execute(
            select(ContextEntry.entry_type, func.count(ContextEntry.id))
            .group_by(ContextEntry.entry_type)
        )
        type_counts = dict(by_type.all())

        by_source = await db.execute(
            select(ContextEntry.source, func.count(ContextEntry.id))
            .group_by(ContextEntry.source)
        )
        source_counts = dict(by_source.all())

        by_tier = await db.execute(
            select(ContextEntry.importance_tier, func.count(ContextEntry.id))
            .group_by(ContextEntry.importance_tier)
        )
        tier_counts = dict(by_tier.all())

        lines = [
            "## Brain Overview",
            f"**Total entries:** {total_count}",
            "",
            "### By Type",
            *[f"- {t}: {c}" for t, c in sorted(type_counts.items(), key=lambda x: -x[1])],
            "",
            "### By Source",
            *[f"- {s}: {c}" for s, c in sorted(source_counts.items(), key=lambda x: -x[1])],
            "",
            "### By Importance",
            *[f"- {t}: {c}" for t, c in sorted(tier_counts.items())],
        ]
        return "\n".join(lines)

    results = await hybrid_search(db, topic, limit=15)

    lines = [f"## Context Summary: {topic}", ""]

    if not results:
        lines.append(f"No entries found for \"{topic}\".")
        return "\n".join(lines)

    # Group by type
    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r["entry_type"], []).append(r)

    for entry_type, entries in by_type.items():
        lines.append(f"### {entry_type.title()} ({len(entries)})")
        for e in entries:
            lines.append(f"**{e['title']}** (tier: {e['importance_tier']}, mentions: {e['mention_count']})")
            body_lines = e["body"].split("\n")
            # Show first meaningful lines
            for bl in body_lines[:4]:
                bl = bl.strip()
                if bl and not bl.startswith("#"):
                    lines.append(f"> {bl}")
                    break
            lines.append("")

    lines.append(f"---\n**{len(results)} entries** across {len(by_type)} categories")
    return "\n".join(lines)


async def _run_analyze_blocker(db: AsyncSession, input_data: dict) -> str:
    """Analyze a blocked task using brain context."""
    task_id = input_data.get("task_id")

    if task_id:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
    else:
        # Get first blocked task
        result = await db.execute(
            select(Task).where(Task.status == "blocked").limit(1)
        )
        task = result.scalar_one_or_none()

    if not task:
        # Show all blocked tasks
        result = await db.execute(
            select(Task).where(Task.status == "blocked")
        )
        blocked = result.scalars().all()
        if not blocked:
            return "## Blocker Analysis\n\nNo blocked tasks found."

        lines = ["## Blocked Tasks", ""]
        for t in blocked:
            lines.append(f"- **{t.title}** — {t.blocker or 'No blocker specified'}")
        return "\n".join(lines)

    lines = [
        "## Blocker Analysis",
        f"### Task: {task.title}",
        f"**Status:** {task.status} | **Urgency:** {task.urgency}",
        f"**Blocker:** {task.blocker or 'Not specified'}",
        "",
    ]

    # Search brain for related context
    search_q = task.title
    if task.blocker:
        search_q += " " + task.blocker
    results = await hybrid_search(db, search_q, limit=5)

    if results:
        lines.append("### Related Brain Context")
        for r in results:
            lines.append(f"- **{r['title']}** ({r['entry_type']}): {r['body'][:150]}...")
        lines.append("")

    lines.append("### Suggested Actions")
    lines.append("1. Review the related context above for dependencies")
    lines.append("2. Check if the blocker involves another team member's input")
    lines.append("3. Consider if the task can be descoped or split")

    return "\n".join(lines)


async def _run_draft_message(db: AsyncSession, input_data: dict) -> str:
    """Search brain for context about a recipient."""
    recipient = input_data.get("recipient", "")
    intent = input_data.get("intent", "")

    if not recipient:
        return "## Draft Message\n\nProvide a recipient name to search brain context."

    results = await hybrid_search(db, recipient, limit=8)

    lines = [
        "## Message Context",
        f"### Recipient: {recipient}",
        f"### Intent: {intent or 'Not specified'}",
        "",
    ]

    if results:
        lines.append("### What the brain knows")
        for r in results:
            lines.append(f"**{r['title']}** ({r['entry_type']}, {r['importance_tier']})")
            body_preview = r["body"][:200].replace("\n", " ")
            lines.append(f"> {body_preview}")
            lines.append("")
    else:
        lines.append(f"No brain entries found for \"{recipient}\".")

    lines.append("---")
    lines.append("*Use this context to draft your message. Add ANTHROPIC_API_KEY to .env for AI-drafted messages.*")

    return "\n".join(lines)
