from __future__ import annotations

import hashlib
from pathlib import Path

import frontmatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import Skill

SKILLS_DIR = Path(__file__).parent.parent / "skills"


async def load_all_skills(db: AsyncSession) -> int:
    """Scan skills/ directory, parse markdown files, upsert into DB."""
    if not SKILLS_DIR.exists():
        return 0

    count = 0
    for md_file in SKILLS_DIR.glob("*.md"):
        post = frontmatter.load(str(md_file))
        meta = post.metadata

        name = meta.get("name", md_file.stem)
        content_hash = hashlib.sha256(post.content.encode()).hexdigest()

        # Check if exists
        result = await db.execute(select(Skill).where(Skill.name == name))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.markdown_hash == content_hash:
                continue  # No change
            existing.display_name = meta.get("display_name", name)
            existing.description = meta.get("description", "")
            existing.markdown_path = str(md_file)
            existing.markdown_hash = content_hash
            existing.trigger_conditions = meta.get("trigger_conditions", {})
            existing.input_schema = meta.get("input_schema", {})
        else:
            skill = Skill(
                name=name,
                display_name=meta.get("display_name", name),
                description=meta.get("description", ""),
                markdown_path=str(md_file),
                markdown_hash=content_hash,
                trigger_conditions=meta.get("trigger_conditions", {}),
                input_schema=meta.get("input_schema", {}),
            )
            db.add(skill)

        count += 1

    await db.commit()
    return count
