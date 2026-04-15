from __future__ import annotations

import os
import uuid

from openai import AsyncOpenAI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.config import settings
from cbrain.db.models import ContextEntry, TimelineEvent

_openai_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


async def generate_embedding(text_content: str) -> list[float]:
    """Generate embedding using OpenAI text-embedding-3-large (3072 dims)."""
    client = _get_openai()
    response = await client.embeddings.create(
        model="text-embedding-3-large",
        input=text_content[:8000],  # Truncate to avoid token limits
    )
    return response.data[0].embedding


async def create_entry(
    db: AsyncSession,
    title: str,
    body: str,
    entry_type: str = "fact",
    source: str = "manual",
    tags: list[str] | None = None,
    source_id: str | None = None,
) -> ContextEntry:
    """Create a new context entry with embedding and timeline event."""
    # Generate embedding
    embedding = await generate_embedding(f"{title}\n{body}")

    entry = ContextEntry(
        title=title,
        body=body,
        body_embedding=embedding,
        entry_type=entry_type,
        source=source,
        source_id=source_id,
        tags=tags or [],
    )
    db.add(entry)

    # Create timeline event
    event = TimelineEvent(
        context_entry_id=entry.id,
        event_type="created",
        summary=f"Created {entry_type}: {title}",
        source=source,
        actor="system",
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def update_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    body: str | None = None,
    title: str | None = None,
    actor: str = "system",
) -> ContextEntry:
    """Update compiled truth and create timeline event."""
    result = await db.execute(select(ContextEntry).where(ContextEntry.id == entry_id))
    entry = result.scalar_one()

    if title:
        entry.title = title
    if body:
        entry.body = body
        entry.body_embedding = await generate_embedding(f"{entry.title}\n{body}")

    # Timeline event for the update
    event = TimelineEvent(
        context_entry_id=entry.id,
        event_type="updated",
        summary=f"Updated compiled truth for: {entry.title}",
        source="agent",
        actor=actor,
    )
    db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry


async def bump_mentions(db: AsyncSession, entry_id: uuid.UUID) -> ContextEntry:
    """Increment mention count and auto-promote importance tier."""
    result = await db.execute(select(ContextEntry).where(ContextEntry.id == entry_id))
    entry = result.scalar_one()

    entry.mention_count += 1
    entry.last_mentioned_at = func.now()

    # Auto-tier promotion
    if entry.mention_count >= 15:
        entry.importance_tier = "critical"
    elif entry.mention_count >= 7:
        entry.importance_tier = "high"
    elif entry.mention_count >= 3:
        entry.importance_tier = "medium"

    await db.commit()
    return entry


async def hybrid_search(
    db: AsyncSession,
    query: str,
    entry_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Hybrid search combining vector similarity and keyword (tsvector) with RRF fusion."""
    if not query.strip():
        # No query — return recent entries
        q = select(ContextEntry).order_by(ContextEntry.updated_at.desc()).limit(limit)
        if entry_type:
            q = q.where(ContextEntry.entry_type == entry_type)
        result = await db.execute(q)
        entries = result.scalars().all()
        return [_entry_dict(e, score=0.0) for e in entries]

    # Generate query embedding
    query_embedding = await generate_embedding(query)

    # Vector search — top N by cosine similarity
    vector_sql = text("""
        SELECT id, title, body, entry_type, source, importance_tier, mention_count,
               tags, created_at, updated_at,
               1 - (body_embedding <=> :embedding::vector) AS vector_score
        FROM context_entries
        WHERE body_embedding IS NOT NULL
        ORDER BY body_embedding <=> :embedding::vector
        LIMIT :limit
    """)

    vector_result = await db.execute(
        vector_sql,
        {"embedding": str(query_embedding), "limit": limit},
    )
    vector_rows = vector_result.mappings().all()

    # Keyword search — top N by ts_rank
    keyword_sql = text("""
        SELECT id, title, body, entry_type, source, importance_tier, mention_count,
               tags, created_at, updated_at,
               ts_rank(to_tsvector('english', title || ' ' || body),
                       plainto_tsquery('english', :query)) AS keyword_score
        FROM context_entries
        WHERE to_tsvector('english', title || ' ' || body)
              @@ plainto_tsquery('english', :query)
        ORDER BY keyword_score DESC
        LIMIT :limit
    """)

    keyword_result = await db.execute(keyword_sql, {"query": query, "limit": limit})
    keyword_rows = keyword_result.mappings().all()

    # RRF fusion
    K = 60  # Standard RRF constant
    rrf_scores: dict[str, float] = {}
    entries_by_id: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        entry_id = str(row["id"])
        rrf_scores[entry_id] = rrf_scores.get(entry_id, 0) + 1.0 / (K + rank + 1)
        entries_by_id[entry_id] = dict(row)

    for rank, row in enumerate(keyword_rows):
        entry_id = str(row["id"])
        rrf_scores[entry_id] = rrf_scores.get(entry_id, 0) + 1.0 / (K + rank + 1)
        entries_by_id[entry_id] = dict(row)

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    # Apply entry_type filter
    results = []
    for entry_id in sorted_ids[:limit]:
        row = entries_by_id[entry_id]
        if entry_type and row["entry_type"] != entry_type:
            continue
        results.append({
            "id": entry_id,
            "title": row["title"],
            "body": row["body"][:500],  # Truncate for search results
            "entry_type": row["entry_type"],
            "source": row["source"],
            "importance_tier": row["importance_tier"],
            "mention_count": row["mention_count"],
            "tags": row["tags"] or [],
            "score": round(rrf_scores[entry_id], 6),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })

    return results


def _entry_dict(entry: ContextEntry, score: float = 0.0) -> dict:
    return {
        "id": str(entry.id),
        "title": entry.title,
        "body": entry.body[:500],
        "entry_type": entry.entry_type,
        "source": entry.source,
        "importance_tier": entry.importance_tier,
        "mention_count": entry.mention_count,
        "tags": entry.tags or [],
        "score": score,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }
