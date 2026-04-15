from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.config import settings
from cbrain.db.models import SyncState, TimelineEvent
from cbrain.services.context_store import create_entry
from cbrain.services.signal_detector import detect_signals
from cbrain.services.task_engine import upsert_task

logger = logging.getLogger(__name__)


async def sync_notion(db: AsyncSession) -> dict:
    """Sync tasks and pages from Notion workspace."""
    import httpx

    api_key = settings.notion_api_key
    if not api_key:
        return {"error": "NOTION_API_KEY not configured", "tasks_synced": 0, "pages_synced": 0}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    # Get sync cursor
    result = await db.execute(select(SyncState).where(SyncState.source == "notion"))
    sync_state = result.scalar_one_or_none()
    last_sync = sync_state.last_sync_at if sync_state else None

    tasks_synced = 0
    pages_synced = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for all pages modified since last sync
        search_body: dict = {
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": 50,
        }
        if last_sync:
            search_body["filter"] = {"property": "object", "value": "page"}

        try:
            resp = await client.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json=search_body,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Notion search failed: {e}")
            return {"error": str(e), "tasks_synced": 0, "pages_synced": 0}

        for page in data.get("results", []):
            if page.get("object") != "page":
                continue

            page_id = page["id"]
            title = _extract_title(page)
            last_edited = page.get("last_edited_time", "")

            # Skip if not modified since last sync
            if last_sync and last_edited:
                edited_dt = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                if edited_dt <= last_sync:
                    continue

            # Check if it looks like a task (has status/checkbox properties)
            properties = page.get("properties", {})
            is_task = any(
                prop.get("type") in ("status", "checkbox", "select")
                and key.lower() in ("status", "done", "complete", "state")
                for key, prop in properties.items()
            )

            if is_task:
                # Sync as task
                description = _extract_property_text(properties, ["description", "notes", "details"])
                urgency = _extract_urgency(properties)
                due = _extract_date(properties, ["due", "due_date", "deadline"])

                await upsert_task(
                    db,
                    title=title,
                    description=description,
                    source="notion",
                    source_id=page_id,
                    urgency=urgency,
                    due_date=due,
                )
                tasks_synced += 1
            else:
                # Sync as context entry — fetch page content
                try:
                    blocks_resp = await client.get(
                        f"https://api.notion.com/v1/blocks/{page_id}/children",
                        headers=headers,
                    )
                    blocks_resp.raise_for_status()
                    blocks = blocks_resp.json().get("results", [])
                    body = _blocks_to_text(blocks)
                except Exception:
                    body = title

                if body.strip():
                    # Run signal detection
                    signals = await detect_signals(body, source="notion")

                    # Create context entry
                    await create_entry(
                        db,
                        title=title,
                        body=body[:5000],
                        entry_type="project" if len(body) > 500 else "fact",
                        source="notion",
                        source_id=page_id,
                    )
                    pages_synced += 1

                    # Create tasks from detected action items
                    for signal in signals:
                        if signal.signal_type == "action_item":
                            await upsert_task(
                                db,
                                title=signal.title,
                                description=signal.body,
                                source="notion_signal",
                                source_id=f"{page_id}:{signal.title}",
                                urgency=signal.urgency,
                            )
                            tasks_synced += 1

    # Update sync state
    if sync_state:
        sync_state.last_sync_at = datetime.now()
    else:
        sync_state = SyncState(source="notion", last_sync_at=datetime.now())
        db.add(sync_state)

    # Timeline event
    event = TimelineEvent(
        event_type="sync",
        summary=f"Notion sync: {tasks_synced} tasks, {pages_synced} pages",
        source="notion",
        actor="notion_sync",
    )
    db.add(event)

    await db.commit()
    return {"tasks_synced": tasks_synced, "pages_synced": pages_synced}


def _extract_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


def _extract_property_text(properties: dict, keys: list[str]) -> str | None:
    for key in keys:
        for prop_name, prop in properties.items():
            if prop_name.lower() == key.lower() and prop.get("type") == "rich_text":
                parts = prop.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in parts)
                if text:
                    return text
    return None


def _extract_urgency(properties: dict) -> str:
    for prop_name, prop in properties.items():
        if prop_name.lower() in ("priority", "urgency"):
            if prop.get("type") == "select" and prop.get("select"):
                val = prop["select"].get("name", "").lower()
                if val in ("critical", "high", "normal", "low"):
                    return val
    return "normal"


def _extract_date(properties: dict, keys: list[str]):
    for key in keys:
        for prop_name, prop in properties.items():
            if prop_name.lower() == key.lower() and prop.get("type") == "date":
                date_obj = prop.get("date")
                if date_obj and date_obj.get("start"):
                    return datetime.fromisoformat(date_obj["start"])
    return None


def _blocks_to_text(blocks: list[dict]) -> str:
    """Convert Notion blocks to plain text."""
    parts = []
    for block in blocks:
        block_type = block.get("type", "")
        content = block.get(block_type, {})
        if isinstance(content, dict):
            rich_text = content.get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rich_text)
            if text:
                parts.append(text)
    return "\n".join(parts)
