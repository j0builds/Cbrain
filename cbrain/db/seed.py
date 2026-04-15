"""Seed the database with team members and initial data."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from cbrain.db.engine import async_session
from cbrain.db.models import TeamMember


TEAM = [
    {
        "name": "Joseph",
        "role": "CEO",
        "slug": "joseph",
        "memory_path": "/Users/jo/.claude/projects/-Users-jo/memory",
        "is_ceo": True,
    },
    {
        "name": "Vardon",
        "role": "Co-founder",
        "slug": "vardon",
        "memory_path": None,
        "is_ceo": False,
    },
    {
        "name": "Keshav",
        "role": "Co-founder",
        "slug": "keshav",
        "memory_path": None,
        "is_ceo": False,
    },
]


async def seed():
    async with async_session() as db:
        for member in TEAM:
            result = await db.execute(
                select(TeamMember).where(TeamMember.slug == member["slug"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(TeamMember(**member))
                print(f"  Created team member: {member['name']} ({member['role']})")
            else:
                print(f"  Team member exists: {member['name']}")

        await db.commit()

        # Load skills
        from cbrain.services.skill_loader import load_all_skills

        count = await load_all_skills(db)
        print(f"  Loaded {count} skills")


if __name__ == "__main__":
    asyncio.run(seed())
