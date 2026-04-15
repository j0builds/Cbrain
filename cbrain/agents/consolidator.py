from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.agents.base import AgentRunResult, BaseAgent
from cbrain.db.models import ContextEntry, TimelineEvent
from cbrain.services.claude_client import ask_claude
from cbrain.services.context_store import generate_embedding


class ConsolidatorAgent(BaseAgent):
    name = "consolidator"

    async def execute(self, db: AsyncSession) -> AgentRunResult:
        """Merge recent signals, update compiled truth, deduplicate."""
        actions = []

        # Get recent timeline events (last 24 hours)
        since = datetime.now() - timedelta(hours=24)
        tl_q = (
            select(TimelineEvent)
            .where(TimelineEvent.created_at >= since)
            .order_by(TimelineEvent.created_at.desc())
            .limit(100)
        )
        tl_result = await db.execute(tl_q)
        events = tl_result.scalars().all()

        if not events:
            return AgentRunResult(summary="No recent events to consolidate.")

        # Group events by context_entry_id
        entry_events: dict[str, list[TimelineEvent]] = {}
        for event in events:
            if event.context_entry_id:
                key = str(event.context_entry_id)
                entry_events.setdefault(key, []).append(event)

        # For entries with multiple recent events, consolidate
        consolidated = 0
        for entry_id, entry_evts in entry_events.items():
            if len(entry_evts) < 2:
                continue

            result = await db.execute(
                select(ContextEntry).where(ContextEntry.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                continue

            # Build events summary for Claude
            events_text = "\n".join([
                f"- [{e.event_type}] {e.summary} (source: {e.source})"
                for e in entry_evts
            ])

            system = """You are the consolidator for C-Brain. Given an entity's current
compiled truth and recent events about it, produce an updated compiled truth that
integrates the new information. Keep it concise but comprehensive. Return ONLY the
updated text."""

            prompt = f"""Entity: {entry.title}
Type: {entry.entry_type}

Current compiled truth:
{entry.body}

Recent events (last 24h):
{events_text}

Write the updated compiled truth."""

            try:
                response = await ask_claude(prompt, system=system, max_tokens=2048)
                entry.body = response.text.strip()
                entry.body_embedding = await generate_embedding(
                    f"{entry.title}\n{entry.body}"
                )

                # Record consolidation
                consolidation_event = TimelineEvent(
                    context_entry_id=entry.id,
                    event_type="consolidation",
                    summary=f"Consolidated {len(entry_evts)} events into compiled truth",
                    source="agent",
                    actor="consolidator",
                )
                db.add(consolidation_event)
                consolidated += 1

                actions.append({
                    "type": "consolidated",
                    "entry_id": entry_id,
                    "title": entry.title,
                    "events_merged": len(entry_evts),
                })
            except Exception:
                continue

        await db.commit()
        return AgentRunResult(
            summary=f"Consolidated {consolidated} entries from {len(events)} recent events.",
            actions=actions,
        )
