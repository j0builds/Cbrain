from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cbrain.db.models import ContextEntry, TimelineEvent
from cbrain.deps import DBSession

router = APIRouter()


class ContextCreate(BaseModel):
    title: str
    body: str
    entry_type: str = "fact"
    source: str = "manual"
    tags: list[str] = []


@router.get("/search")
async def search_context(db: DBSession, q: str = "", entry_type: str | None = None, limit: int = 20):
    from cbrain.services.context_store import hybrid_search

    results = await hybrid_search(db, q, entry_type=entry_type, limit=limit)
    return results


@router.get("/{entry_id}")
async def get_context_entry(entry_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(ContextEntry).where(ContextEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Context entry not found")

    # Get timeline
    tl_q = (
        select(TimelineEvent)
        .where(TimelineEvent.context_entry_id == entry_id)
        .order_by(TimelineEvent.created_at.desc())
        .limit(50)
    )
    tl_result = await db.execute(tl_q)
    timeline = tl_result.scalars().all()

    return {
        "id": str(entry.id),
        "title": entry.title,
        "body": entry.body,
        "entry_type": entry.entry_type,
        "source": entry.source,
        "importance_tier": entry.importance_tier,
        "mention_count": entry.mention_count,
        "tags": entry.tags or [],
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "timeline": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "summary": e.summary,
                "source": e.source,
                "actor": e.actor,
                "created_at": e.created_at.isoformat(),
            }
            for e in timeline
        ],
    }


@router.post("", status_code=201)
async def create_context_entry(body: ContextCreate, db: DBSession):
    from cbrain.services.context_store import create_entry

    entry = await create_entry(db, body.title, body.body, body.entry_type, body.source, body.tags)
    return {"id": str(entry.id), "title": entry.title}
