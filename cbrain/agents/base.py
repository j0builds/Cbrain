from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import AgentRun


@dataclass
class AgentRunResult:
    summary: str
    actions: list[dict] = field(default_factory=list)


class BaseAgent(ABC):
    name: str = "unnamed"

    async def run(self, db: AsyncSession) -> AgentRun:
        run = AgentRun(agent_name=self.name, status="running")
        db.add(run)
        await db.flush()

        start = time.monotonic()
        try:
            result = await self.execute(db)
            run.status = "completed"
            run.summary = result.summary
            run.actions_taken = result.actions
        except Exception as e:
            run.status = "failed"
            run.errors = [str(e)]
            run.summary = f"Failed: {e}"

        run.completed_at = datetime.now()
        run.duration_ms = int((time.monotonic() - start) * 1000)
        await db.commit()
        await db.refresh(run)
        return run

    @abstractmethod
    async def execute(self, db: AsyncSession) -> AgentRunResult:
        ...


def get_agent(name: str) -> BaseAgent:
    from cbrain.agents.consolidator import ConsolidatorAgent
    from cbrain.agents.enricher import EnricherAgent
    from cbrain.agents.prioritizer import PrioritizerAgent
    from cbrain.agents.question_generator import QuestionGeneratorAgent

    agents = {
        "consolidator": ConsolidatorAgent,
        "prioritizer": PrioritizerAgent,
        "enricher": EnricherAgent,
        "question_generator": QuestionGeneratorAgent,
    }
    cls = agents.get(name)
    if not cls:
        raise ValueError(f"Unknown agent: {name}")
    return cls()
