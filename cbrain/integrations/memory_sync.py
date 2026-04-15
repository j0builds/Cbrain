from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import frontmatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.config import settings
from cbrain.db.models import SyncState, TimelineEvent
from cbrain.services.context_store import create_entry
from cbrain.services.signal_detector import detect_signals
from cbrain.services.task_engine import upsert_task

logger = logging.getLogger(__name__)


async def sync_memory(db: AsyncSession) -> dict:
    """Sync Claude memory files from configured paths."""
    paths = settings.memory_path_list
    if not paths:
        return {"error": "No memory paths configured", "entries_synced": 0}

    entries_synced = 0
    tasks_created = 0

    for memory_dir in paths:
        memory_path = Path(memory_dir)
        if not memory_path.exists():
            logger.warning(f"Memory path does not exist: {memory_dir}")
            continue

        # Get sync state for this path
        source_key = f"memory:{memory_dir}"
        result = await db.execute(select(SyncState).where(SyncState.source == source_key))
        sync_state = result.scalar_one_or_none()
        last_sync_ts = sync_state.last_sync_at.timestamp() if sync_state and sync_state.last_sync_at else 0

        # Scan all markdown files
        for md_file in memory_path.glob("*.md"):
            if md_file.name == "MEMORY.md":
                continue  # Skip index file

            # Check mtime
            mtime = md_file.stat().st_mtime
            if mtime <= last_sync_ts:
                continue

            try:
                post = frontmatter.load(str(md_file))
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")
                continue

            meta = post.metadata
            name = meta.get("name", md_file.stem)
            mem_type = meta.get("type", "fact")
            description = meta.get("description", "")
            body = post.content

            if not body.strip():
                continue

            # Map memory types to context entry types
            entry_type_map = {
                "user": "entity",
                "feedback": "decision",
                "project": "project",
                "reference": "fact",
            }
            entry_type = entry_type_map.get(mem_type, "fact")

            # Create context entry
            await create_entry(
                db,
                title=name,
                body=body,
                entry_type=entry_type,
                source="memory",
                source_id=str(md_file),
                tags=[mem_type, "memory"],
            )
            entries_synced += 1

            # Detect signals for action items
            signals = await detect_signals(body, source="memory")
            for signal in signals:
                if signal.signal_type == "action_item":
                    await upsert_task(
                        db,
                        title=signal.title,
                        description=signal.body,
                        source="memory_signal",
                        source_id=f"{md_file}:{signal.title}",
                        urgency=signal.urgency,
                    )
                    tasks_created += 1

        # Update sync state
        if sync_state:
            sync_state.last_sync_at = datetime.now()
        else:
            sync_state = SyncState(source=source_key, last_sync_at=datetime.now())
            db.add(sync_state)

    # Timeline event
    event = TimelineEvent(
        event_type="sync",
        summary=f"Memory sync: {entries_synced} entries, {tasks_created} tasks",
        source="memory",
        actor="memory_sync",
    )
    db.add(event)

    await db.commit()
    return {"entries_synced": entries_synced, "tasks_created": tasks_created}
