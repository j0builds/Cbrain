"""Ingest jopedia wiki articles into C-Brain context store."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import frontmatter
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import SyncState, TimelineEvent
from cbrain.services.context_store import create_entry, find_by_source

logger = logging.getLogger(__name__)

# Map jopedia categories to C-Brain entry types
CATEGORY_TYPE_MAP = {
    "people": "entity",
    "companies": "entity",
    "institutions": "entity",
    "projects": "project",
    "concepts": "fact",
    "strategies": "decision",
    "patterns": "decision",
    "events": "fact",
    "artifacts": "fact",
    "philosophies": "fact",
    "tools": "fact",
    "eras": "fact",
    "books": "fact",
    "platforms": "fact",
    "ideas": "fact",
    "decisions": "decision",
}


async def sync_jopedia(db: AsyncSession, jopedia_path: str = "/tmp/jopedia") -> dict:
    """Ingest all wiki articles from jopedia into C-Brain."""
    wiki_dir = Path(jopedia_path) / "wiki"
    if not wiki_dir.exists():
        return {"error": f"Wiki directory not found: {wiki_dir}", "articles_synced": 0}

    # Get sync state
    source_key = "jopedia"
    from sqlalchemy import select
    result = await db.execute(select(SyncState).where(SyncState.source == source_key))
    sync_state = result.scalar_one_or_none()

    articles_created = 0
    articles_updated = 0
    articles_skipped = 0

    # Walk all category directories
    for category_dir in sorted(wiki_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        if category.startswith("_") or category.startswith("."):
            continue

        entry_type = CATEGORY_TYPE_MAP.get(category, "fact")

        for md_file in sorted(category_dir.glob("*.md")):
            source_id = f"jopedia:{category}/{md_file.stem}"

            try:
                post = frontmatter.load(str(md_file))
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")
                continue

            title = post.metadata.get("title", md_file.stem.replace("-", " ").title())
            body = post.content.strip()
            if not body:
                continue

            # Extract tags from frontmatter
            tags = [category]
            related = post.metadata.get("related", [])
            if isinstance(related, list):
                for r in related:
                    if isinstance(r, list):
                        tags.extend([link.strip("[]") for link in r])
                    elif isinstance(r, str):
                        tags.append(r.strip("[]"))

            article_type = post.metadata.get("type", entry_type)
            if article_type in CATEGORY_TYPE_MAP:
                entry_type_resolved = CATEGORY_TYPE_MAP[article_type]
            else:
                entry_type_resolved = entry_type

            # Check if already exists
            existing = await find_by_source(db, "jopedia", source_id)
            if existing:
                # Check if content changed
                if existing.body == body:
                    articles_skipped += 1
                    continue
                # Update
                existing.body = body
                existing.title = title
                existing.tags = tags[:10]  # Cap tags
                articles_updated += 1
            else:
                # Determine importance tier based on body length and links
                link_count = body.count("[[")
                if link_count >= 10 or len(body) > 3000:
                    importance = "high"
                elif link_count >= 5 or len(body) > 1500:
                    importance = "medium"
                else:
                    importance = "low"

                entry = await create_entry(
                    db,
                    title=title,
                    body=body,
                    entry_type=entry_type_resolved,
                    source="jopedia",
                    source_id=source_id,
                    tags=tags[:10],
                    metadata={
                        "category": category,
                        "created": str(post.metadata.get("created", "")),
                        "last_updated": str(post.metadata.get("last_updated", "")),
                        "sources": post.metadata.get("sources", []),
                    },
                )
                entry.importance_tier = importance
                entry.mention_count = max(1, link_count)
                articles_created += 1

    # Update sync state
    if sync_state:
        sync_state.last_sync_at = datetime.now()
        sync_state.sync_metadata = {
            "created": articles_created,
            "updated": articles_updated,
            "skipped": articles_skipped,
        }
    else:
        sync_state = SyncState(
            source=source_key,
            last_sync_at=datetime.now(),
            sync_metadata={
                "created": articles_created,
                "updated": articles_updated,
                "skipped": articles_skipped,
            },
        )
        db.add(sync_state)

    # Timeline event
    event = TimelineEvent(
        event_type="sync",
        summary=f"Jopedia sync: {articles_created} created, {articles_updated} updated, {articles_skipped} unchanged",
        source="jopedia",
        actor="jopedia_sync",
    )
    db.add(event)

    await db.commit()
    return {
        "articles_created": articles_created,
        "articles_updated": articles_updated,
        "articles_skipped": articles_skipped,
    }
