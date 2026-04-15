"""Sync Claude memory files into C-Brain context store."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import frontmatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.config import settings
from cbrain.db.models import SyncState, TimelineEvent
from cbrain.services.context_store import create_entry, find_by_source

logger = logging.getLogger(__name__)

TYPE_MAP = {
    "user": "entity",
    "feedback": "decision",
    "project": "project",
    "reference": "fact",
}


async def sync_memory(db: AsyncSession) -> dict:
    """Sync Claude memory files from configured paths."""
    paths = settings.memory_path_list
    if not paths:
        return {"error": "No memory paths configured", "entries_synced": 0}

    entries_created = 0
    entries_skipped = 0

    for memory_dir in paths:
        memory_path = Path(memory_dir)
        if not memory_path.exists():
            logger.warning(f"Memory path does not exist: {memory_dir}")
            continue

        source_key = f"memory:{memory_dir}"
        result = await db.execute(select(SyncState).where(SyncState.source == source_key))
        sync_state = result.scalar_one_or_none()

        for md_file in memory_path.glob("*.md"):
            if md_file.name == "MEMORY.md":
                continue

            source_id = f"memory:{md_file}"

            try:
                post = frontmatter.load(str(md_file))
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")
                continue

            meta = post.metadata
            name = meta.get("name", md_file.stem)
            mem_type = meta.get("type", "fact")
            body = post.content.strip()
            if not body:
                continue

            # Skip if already ingested with same content
            existing = await find_by_source(db, "memory", source_id)
            if existing:
                if existing.body == body:
                    entries_skipped += 1
                    continue
                existing.body = body
                existing.title = name
                entries_created += 1  # count as update
                continue

            entry_type = TYPE_MAP.get(mem_type, "fact")

            await create_entry(
                db,
                title=name,
                body=body,
                entry_type=entry_type,
                source="memory",
                source_id=source_id,
                tags=[mem_type, "memory"],
            )
            entries_created += 1

        if sync_state:
            sync_state.last_sync_at = datetime.now()
        else:
            sync_state = SyncState(source=source_key, last_sync_at=datetime.now())
            db.add(sync_state)

    event = TimelineEvent(
        event_type="sync",
        summary=f"Memory sync: {entries_created} entries ingested, {entries_skipped} unchanged",
        source="memory",
        actor="memory_sync",
    )
    db.add(event)

    await db.commit()
    return {"entries_synced": entries_created, "entries_skipped": entries_skipped}
