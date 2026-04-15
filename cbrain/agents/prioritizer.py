from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.agents.base import AgentRunResult, BaseAgent
from cbrain.db.models import Task
from cbrain.services.claude_client import ask_claude


class PrioritizerAgent(BaseAgent):
    name = "prioritizer"

    async def execute(self, db: AsyncSession) -> AgentRunResult:
        """Re-rank all open tasks for the CEO."""
        q = (
            select(Task)
            .where(Task.status.in_(["open", "in_progress", "blocked"]))
            .order_by(Task.created_at.desc())
            .limit(50)
        )
        result = await db.execute(q)
        tasks = result.scalars().all()

        if not tasks:
            return AgentRunResult(summary="No open tasks to prioritize.")

        tasks_text = "\n".join([
            f"- ID: {t.id} | Title: {t.title} | Status: {t.status} | "
            f"Urgency: {t.urgency} | Blocker: {t.blocker or 'none'} | "
            f"Current priority: {t.priority}"
            for t in tasks
        ])

        system = """You are the CEO task prioritizer for C-Brain (Cognitionus startup).
The CEO is Joseph. The team is Joseph, Vardon, and Keshav.

Prioritization framework (highest to lowest):
1. BLOCKING OTHERS — If Joseph's inaction blocks Vardon or Keshav, that's P0
2. TIME-SENSITIVE EXTERNAL — Investor replies, partner deadlines, customer follow-ups
3. REVENUE-GENERATING — Anything moving the needle on paying customers
4. STRATEGIC DECISIONS — Only Joseph can make these; don't let them rot
5. OPERATIONAL — Important but can wait 24-48 hours

Rules:
- Maximum 7 tasks in top tier (priority 0-10). CEO can only focus on 7 things.
- Tasks open >14 days with no activity: demote or suggest dismissal.
- Always explain WHY in priority_reason.
- Return JSON array: [{"task_id": "...", "priority": N, "priority_reason": "..."}]
- Return ONLY valid JSON."""

        prompt = f"Current open tasks:\n{tasks_text}\n\nPrioritize these tasks."

        response = await ask_claude(
            prompt,
            system=system,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
        )

        try:
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            updates = json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            return AgentRunResult(summary="Failed to parse prioritization response.")

        # Apply updates
        task_map = {str(t.id): t for t in tasks}
        actions = []
        for update in updates:
            task_id = update.get("task_id")
            task = task_map.get(task_id)
            if not task:
                continue
            task.priority = update.get("priority", task.priority)
            task.priority_reason = update.get("priority_reason", task.priority_reason)
            actions.append({
                "type": "reprioritized",
                "task_id": task_id,
                "title": task.title,
                "new_priority": task.priority,
                "reason": task.priority_reason,
            })

        await db.commit()
        return AgentRunResult(
            summary=f"Reprioritized {len(actions)} tasks.",
            actions=actions,
        )
