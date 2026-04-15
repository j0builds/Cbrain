from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cbrain.db.models import Skill, SkillExecution
from cbrain.deps import DBSession

router = APIRouter()


class SkillExecuteBody(BaseModel):
    input_data: dict = {}
    triggered_by: str = "user"


@router.get("")
async def list_skills(db: DBSession):
    result = await db.execute(select(Skill).order_by(Skill.name))
    skills = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "execution_count": s.execution_count,
            "last_executed_at": s.last_executed_at.isoformat() if s.last_executed_at else None,
        }
        for s in skills
    ]


@router.get("/{skill_id}")
async def get_skill(skill_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {
        "id": str(skill.id),
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "trigger_conditions": skill.trigger_conditions,
        "input_schema": skill.input_schema,
        "execution_count": skill.execution_count,
        "last_executed_at": skill.last_executed_at.isoformat() if skill.last_executed_at else None,
    }


@router.post("/{skill_id}/execute")
async def execute_skill(skill_id: uuid.UUID, body: SkillExecuteBody, db: DBSession):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Import here to avoid circular dependency
    from cbrain.services.skill_executor import execute_skill as run_skill

    execution = await run_skill(db, skill, body.input_data, body.triggered_by)
    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "output_text": execution.output_text,
        "duration_ms": execution.duration_ms,
    }


@router.get("/{skill_id}/executions")
async def list_executions(skill_id: uuid.UUID, db: DBSession, limit: int = 10):
    q = (
        select(SkillExecution)
        .where(SkillExecution.skill_id == skill_id)
        .order_by(SkillExecution.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    executions = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "status": e.status,
            "duration_ms": e.duration_ms,
            "triggered_by": e.triggered_by,
            "model": e.model,
            "created_at": e.created_at.isoformat(),
        }
        for e in executions
    ]


@router.post("/reload")
async def reload_skills(db: DBSession):
    from cbrain.services.skill_loader import load_all_skills

    count = await load_all_skills(db)
    return {"loaded": count}
