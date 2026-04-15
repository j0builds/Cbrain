from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.agents.base import AgentRunResult, BaseAgent
from cbrain.services.enrichment import enrich_promoted_entries


class EnricherAgent(BaseAgent):
    name = "enricher"

    async def execute(self, db: AsyncSession) -> AgentRunResult:
        """Promote entities by mention count and enrich high-tier entries."""
        actions = await enrich_promoted_entries(db)
        return AgentRunResult(
            summary=f"Enriched {len(actions)} entries.",
            actions=actions,
        )
