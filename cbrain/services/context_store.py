from __future__ import annotations

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import ContextEntry, TimelineEvent


async def create_entry(
    db: AsyncSession,
    title: str,
    body: str,
    entry_type: str = "fact",
    source: str = "manual",
    tags: list[str] | None = None,
    source_id: str | None = None,
    metadata: dict | None = None,
) -> ContextEntry:
    """Create a new context entry with timeline event. Embeddings deferred until OpenAI key available."""
    entry = ContextEntry(
        title=title,
        body=body,
        entry_type=entry_type,
        source=source,
        source_id=source_id,
        tags=tags or [],
        metadata_=metadata or {},
    )
    db.add(entry)

    event = TimelineEvent(
        context_entry_id=entry.id,
        event_type="created",
        summary=f"Created {entry_type}: {title}",
        source=source,
        actor="system",
    )
    db.add(event)

    await db.flush()
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

    event = TimelineEvent(
        context_entry_id=entry.id,
        event_type="updated",
        summary=f"Updated: {entry.title}",
        source="agent",
        actor=actor,
    )
    db.add(event)

    await db.flush()
    return entry


async def bump_mentions(db: AsyncSession, entry_id: uuid.UUID) -> ContextEntry:
    """Increment mention count and auto-promote importance tier."""
    result = await db.execute(select(ContextEntry).where(ContextEntry.id == entry_id))
    entry = result.scalar_one()

    entry.mention_count += 1
    entry.last_mentioned_at = func.now()

    if entry.mention_count >= 15:
        entry.importance_tier = "critical"
    elif entry.mention_count >= 7:
        entry.importance_tier = "high"
    elif entry.mention_count >= 3:
        entry.importance_tier = "medium"

    await db.flush()
    return entry


async def find_by_source(db: AsyncSession, source: str, source_id: str) -> ContextEntry | None:
    """Find existing entry by source + source_id."""
    result = await db.execute(
        select(ContextEntry).where(
            ContextEntry.source == source,
            ContextEntry.source_id == source_id,
        )
    )
    return result.scalar_one_or_none()


async def hybrid_search(
    db: AsyncSession,
    query: str,
    entry_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search using PostgreSQL full-text search with ts_rank scoring."""
    if not query.strip():
        q = select(ContextEntry).order_by(ContextEntry.updated_at.desc()).limit(limit)
        if entry_type:
            q = q.where(ContextEntry.entry_type == entry_type)
        result = await db.execute(q)
        entries = result.scalars().all()
        return [_entry_dict(e, score=0.0) for e in entries]

    # Full-text search with ts_rank
    params: dict = {"query": query, "limit": limit}

    type_filter = ""
    if entry_type:
        type_filter = "AND entry_type = :entry_type"
        params["entry_type"] = entry_type

    sql = text(f"""
        SELECT id, title, body, entry_type, source, importance_tier, mention_count,
               tags, created_at, updated_at,
               ts_rank(
                   to_tsvector('english', title || ' ' || body),
                   plainto_tsquery('english', :query)
               ) AS rank_score
        FROM context_entries
        WHERE to_tsvector('english', title || ' ' || body)
              @@ plainto_tsquery('english', :query)
        {type_filter}
        ORDER BY rank_score DESC
        LIMIT :limit
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    # If full-text found nothing, fall back to ILIKE title/body search
    if not rows:
        like_query = f"%{query}%"
        fallback_sql = text(f"""
            SELECT id, title, body, entry_type, source, importance_tier, mention_count,
                   tags, created_at, updated_at,
                   1.0 AS rank_score
            FROM context_entries
            WHERE (title ILIKE :like_q OR body ILIKE :like_q)
            {type_filter}
            ORDER BY updated_at DESC
            LIMIT :limit
        """)
        params["like_q"] = like_query
        result = await db.execute(fallback_sql, params)
        rows = result.mappings().all()

    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "body": row["body"][:500],
            "entry_type": row["entry_type"],
            "source": row["source"],
            "importance_tier": row["importance_tier"],
            "mention_count": row["mention_count"],
            "tags": row["tags"] or [],
            "score": round(float(row["rank_score"]), 6),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


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
