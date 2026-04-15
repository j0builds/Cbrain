"""Sync pages and tasks from Notion workspace into C-Brain."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.config import settings
from cbrain.db.models import SyncState, TimelineEvent
from cbrain.services.context_store import create_entry, find_by_source
from cbrain.services.task_engine import upsert_task

logger = logging.getLogger(__name__)


async def sync_notion(db: AsyncSession) -> dict:
    """Sync tasks and pages from Notion workspace."""
    import httpx

    api_key = settings.get_notion_key()
    if not api_key:
        return {"error": "NOTION_API_KEY not configured", "tasks_synced": 0, "pages_synced": 0}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    tasks_synced = 0
    pages_synced = 0
    errors = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for recent pages
        search_body = {
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": 100,
        }

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
            if not title or title == "Untitled":
                continue

            properties = page.get("properties", {})

            # Detect tasks (pages with status/checkbox properties)
            is_task = any(
                prop.get("type") in ("status", "checkbox", "select")
                and key.lower() in ("status", "done", "complete", "state", "stage")
                for key, prop in properties.items()
            )

            if is_task:
                description = _extract_rich_text(properties, ["description", "notes", "details", "summary"])
                urgency = _extract_select(properties, ["priority", "urgency"])
                due = _extract_date(properties, ["due", "due_date", "deadline", "date"])

                urgency_val = "normal"
                if urgency:
                    ul = urgency.lower()
                    if ul in ("critical", "urgent", "p0"):
                        urgency_val = "critical"
                    elif ul in ("high", "p1"):
                        urgency_val = "high"
                    elif ul in ("low", "p3"):
                        urgency_val = "low"

                await upsert_task(
                    db, title=title, description=description,
                    source="notion", source_id=page_id,
                    urgency=urgency_val, due_date=due,
                )
                tasks_synced += 1
            else:
                # Sync as context entry
                source_id = f"notion:{page_id}"
                existing = await find_by_source(db, "notion", source_id)
                if existing:
                    pages_synced += 1
                    continue

                # Fetch page content blocks
                body = title
                try:
                    blocks_resp = await client.get(
                        f"https://api.notion.com/v1/blocks/{page_id}/children",
                        headers=headers,
                        params={"page_size": 50},
                    )
                    if blocks_resp.status_code == 200:
                        blocks = blocks_resp.json().get("results", [])
                        block_text = _blocks_to_text(blocks)
                        if block_text.strip():
                            body = block_text
                except Exception as e:
                    logger.debug(f"Could not fetch blocks for {page_id}: {e}")

                # Determine entry type from properties
                entry_type = "fact"
                prop_types = {k.lower(): v.get("type") for k, v in properties.items()}
                if any(k in prop_types for k in ["company", "industry"]):
                    entry_type = "entity"
                elif any(k in prop_types for k in ["project", "initiative"]):
                    entry_type = "project"

                await create_entry(
                    db, title=title, body=body[:5000],
                    entry_type=entry_type, source="notion", source_id=source_id,
                    tags=["notion"],
                )
                pages_synced += 1

    # Update sync state
    result = await db.execute(select(SyncState).where(SyncState.source == "notion"))
    sync_state = result.scalar_one_or_none()
    if sync_state:
        sync_state.last_sync_at = datetime.now()
        sync_state.sync_metadata = {"tasks": tasks_synced, "pages": pages_synced}
    else:
        db.add(SyncState(
            source="notion", last_sync_at=datetime.now(),
            sync_metadata={"tasks": tasks_synced, "pages": pages_synced},
        ))

    event = TimelineEvent(
        event_type="sync",
        summary=f"Notion sync: {tasks_synced} tasks, {pages_synced} pages",
        source="notion", actor="notion_sync",
    )
    db.add(event)

    await db.commit()
    return {"tasks_synced": tasks_synced, "pages_synced": pages_synced}


def _extract_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    return "Untitled"


def _extract_rich_text(properties: dict, keys: list[str]) -> str | None:
    for key in keys:
        for prop_name, prop in properties.items():
            if prop_name.lower() == key and prop.get("type") == "rich_text":
                text = "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
                if text:
                    return text
    return None


def _extract_select(properties: dict, keys: list[str]) -> str | None:
    for key in keys:
        for prop_name, prop in properties.items():
            if prop_name.lower() == key:
                if prop.get("type") == "select" and prop.get("select"):
                    return prop["select"].get("name")
                elif prop.get("type") == "status" and prop.get("status"):
                    return prop["status"].get("name")
    return None


def _extract_date(properties: dict, keys: list[str]):
    for key in keys:
        for prop_name, prop in properties.items():
            if prop_name.lower() == key and prop.get("type") == "date":
                date_obj = prop.get("date")
                if date_obj and date_obj.get("start"):
                    try:
                        return datetime.fromisoformat(date_obj["start"])
                    except ValueError:
                        pass
    return None


def _blocks_to_text(blocks: list[dict]) -> str:
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
