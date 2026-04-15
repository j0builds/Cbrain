from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from cbrain.db.models import SyncState
from cbrain.deps import DBSession

router = APIRouter()


@router.post("/sync/notion")
async def trigger_notion_sync(db: DBSession):
    from cbrain.integrations.notion_sync import sync_notion
    result = await sync_notion(db)
    return result


@router.post("/sync/memory")
async def trigger_memory_sync(db: DBSession):
    from cbrain.integrations.memory_sync import sync_memory
    result = await sync_memory(db)
    return result


@router.post("/sync/jopedia")
async def trigger_jopedia_sync(db: DBSession):
    from cbrain.integrations.jopedia_sync import sync_jopedia
    result = await sync_jopedia(db)
    return result


@router.post("/sync/extract-tasks")
async def trigger_task_extraction(db: DBSession):
    from cbrain.services.task_extractor import extract_tasks_from_brain
    result = await extract_tasks_from_brain(db)
    return result


@router.get("/sync/status")
async def sync_status(db: DBSession):
    result = await db.execute(select(SyncState))
    states = result.scalars().all()
    return {
        s.source: {
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
            "metadata": s.sync_metadata,
        }
        for s in states
    }
