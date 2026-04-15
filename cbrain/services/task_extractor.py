"""Extract actionable tasks from context entries across all brain sources.
No LLM needed — uses pattern matching and entry metadata."""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import ContextEntry, Task, TimelineEvent
from cbrain.services.task_engine import upsert_task


async def extract_tasks_from_brain(db: AsyncSession) -> dict:
    """Scan all context entries and extract actionable tasks."""
    created = 0
    skipped = 0

    # 1. All projects become tasks (track each project's status)
    projects = await db.execute(
        select(ContextEntry).where(ContextEntry.entry_type == "project")
    )
    for entry in projects.scalars().all():
        task, is_new = await upsert_task(
            db,
            title=entry.title,
            description=_extract_summary(entry.body),
            source="brain:project",
            source_id=f"ctx:{entry.id}",
            urgency=_tier_to_urgency(entry.importance_tier),
        )
        if is_new:
            task.related_context_ids = [entry.id]
            created += 1
        else:
            skipped += 1

    # 2. Decisions that are pending/active become tasks
    decisions = await db.execute(
        select(ContextEntry).where(ContextEntry.entry_type == "decision")
    )
    for entry in decisions.scalars().all():
        # Skip decisions that are historical/resolved
        body_lower = entry.body.lower()
        if any(w in body_lower for w in ["decided", "resolved", "completed", "shipped", "launched"]):
            # Still create but mark as lower priority
            urgency = "low"
        else:
            urgency = _tier_to_urgency(entry.importance_tier)

        task, is_new = await upsert_task(
            db,
            title=entry.title,
            description=_extract_summary(entry.body),
            source="brain:decision",
            source_id=f"ctx:{entry.id}",
            urgency=urgency,
        )
        if is_new:
            task.related_context_ids = [entry.id]
            created += 1
        else:
            skipped += 1

    # 3. Scan all entries for inline action items (lines with TODO, action, next step patterns)
    all_entries = await db.execute(
        select(ContextEntry).where(ContextEntry.body.ilike("%todo%")
            | ContextEntry.body.ilike("%action item%")
            | ContextEntry.body.ilike("%next step%")
            | ContextEntry.body.ilike("%follow up%")
            | ContextEntry.body.ilike("%need to%")
            | ContextEntry.body.ilike("%should%")
        ).limit(100)
    )
    for entry in all_entries.scalars().all():
        actions = _extract_action_lines(entry.body)
        for action_text in actions[:3]:  # Cap at 3 per entry
            task, is_new = await upsert_task(
                db,
                title=action_text[:200],
                description=f"Extracted from: {entry.title}",
                source="brain:action",
                source_id=f"ctx:{entry.id}:{_hash_short(action_text)}",
                urgency="normal",
            )
            if is_new:
                task.related_context_ids = [entry.id]
                created += 1
            else:
                skipped += 1

    # 4. High-importance entities that might need outreach/follow-up
    high_entities = await db.execute(
        select(ContextEntry).where(
            ContextEntry.entry_type == "entity",
            ContextEntry.importance_tier.in_(["high", "critical"]),
        )
    )
    for entry in high_entities.scalars().all():
        # Create a "review/follow-up" task for important entities
        task, is_new = await upsert_task(
            db,
            title=f"Review: {entry.title}",
            description=_extract_summary(entry.body),
            source="brain:entity",
            source_id=f"ctx:{entry.id}:review",
            urgency="normal",
        )
        if is_new:
            task.related_context_ids = [entry.id]
            created += 1
        else:
            skipped += 1

    # 5. Strategies become tasks (each strategy needs execution)
    strategies = await db.execute(
        select(ContextEntry).where(
            ContextEntry.source == "jopedia",
            ContextEntry.tags.any("strategies"),
        )
    )
    for entry in strategies.scalars().all():
        task, is_new = await upsert_task(
            db,
            title=f"Execute: {entry.title}",
            description=_extract_summary(entry.body),
            source="brain:strategy",
            source_id=f"ctx:{entry.id}:exec",
            urgency="normal",
        )
        if is_new:
            task.related_context_ids = [entry.id]
            created += 1
        else:
            skipped += 1

    # Timeline event
    event = TimelineEvent(
        event_type="task_extraction",
        summary=f"Extracted {created} tasks from brain ({skipped} already existed)",
        source="brain",
        actor="task_extractor",
    )
    db.add(event)
    await db.commit()

    return {"tasks_created": created, "tasks_skipped": skipped}


def _extract_summary(body: str) -> str:
    """Get first meaningful paragraph from body."""
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 20:
            return line[:300]
    return body[:300]


def _extract_action_lines(body: str) -> list[str]:
    """Find lines that look like action items."""
    actions = []
    patterns = [
        r"(?:TODO|Action|Next step|Follow up|Need to)[:\s]+(.+)",
        r"- \[ \]\s+(.+)",  # Markdown unchecked checkbox
        r"(?:should|must|need to)\s+(.{20,120})",
    ]
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                action = match.group(1).strip().rstrip(".")
                if len(action) > 15 and action not in [a for a in actions]:
                    actions.append(action)
                break
    return actions


def _tier_to_urgency(tier: str) -> str:
    return {
        "critical": "critical",
        "high": "high",
        "medium": "normal",
        "low": "low",
    }.get(tier, "normal")


def _hash_short(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:12]
