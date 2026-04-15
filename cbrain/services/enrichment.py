from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import ContextEntry, TimelineEvent
from cbrain.services.claude_client import ask_claude


# Tier thresholds
TIER_THRESHOLDS = {
    "critical": 15,
    "high": 7,
    "medium": 3,
    "low": 1,
}


async def enrich_promoted_entries(db: AsyncSession) -> list[dict]:
    """Find entries that recently crossed a tier threshold and enrich them."""
    actions = []

    # Find entries that might need promotion
    for tier, threshold in [("critical", 15), ("high", 7), ("medium", 3)]:
        q = (
            select(ContextEntry)
            .where(
                ContextEntry.mention_count >= threshold,
                ContextEntry.importance_tier != tier,
                ContextEntry.importance_tier != "critical" if tier != "critical" else True,
            )
            .limit(10)
        )
        result = await db.execute(q)
        entries = result.scalars().all()

        for entry in entries:
            # Determine correct tier
            if entry.mention_count >= 15:
                new_tier = "critical"
            elif entry.mention_count >= 7:
                new_tier = "high"
            elif entry.mention_count >= 3:
                new_tier = "medium"
            else:
                continue

            if new_tier == entry.importance_tier:
                continue

            old_tier = entry.importance_tier
            entry.importance_tier = new_tier

            # Enrich with Claude for high/critical tier
            if new_tier in ("high", "critical"):
                enriched = await _enrich_entry(entry)
                if enriched:
                    entry.body = enriched

            # Timeline event
            event = TimelineEvent(
                context_entry_id=entry.id,
                event_type="enrichment",
                summary=f"Promoted {entry.title} from {old_tier} to {new_tier}",
                source="agent",
                actor="enricher",
                detail={"old_tier": old_tier, "new_tier": new_tier},
            )
            db.add(event)
            actions.append({
                "type": "promoted",
                "entry_id": str(entry.id),
                "title": entry.title,
                "old_tier": old_tier,
                "new_tier": new_tier,
            })

    await db.commit()
    return actions


async def _enrich_entry(entry: ContextEntry) -> str | None:
    """Use Claude to generate a richer compiled truth for the entry."""
    system = """You are the enrichment engine for C-Brain.
Given an entity's current description, enhance it with:
- Clearer structure and organization
- Key relationships and connections
- Strategic implications for a startup CEO
- Open questions or unknowns

Keep the original information but make it more useful for decision-making.
Return ONLY the enriched text, no explanation."""

    prompt = f"""Entity: {entry.title}
Type: {entry.entry_type}
Current description:
{entry.body}

Mentions: {entry.mention_count}
Tags: {', '.join(entry.tags or [])}

Enrich this entry."""

    try:
        response = await ask_claude(prompt, system=system, max_tokens=2048)
        return response.text.strip()
    except Exception:
        return None
