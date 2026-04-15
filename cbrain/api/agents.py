from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from cbrain.db.models import AgentRun
from cbrain.deps import DBSession

router = APIRouter()

AGENT_NAMES = ["consolidator", "prioritizer", "enricher", "question_generator"]


@router.get("/status")
async def agent_status(db: DBSession):
    """Latest run per agent."""
    status = {}
    for name in AGENT_NAMES:
        q = (
            select(AgentRun)
            .where(AgentRun.agent_name == name)
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        result = await db.execute(q)
        run = result.scalar_one_or_none()
        status[name] = {
            "last_run": {
                "id": str(run.id),
                "status": run.status,
                "started_at": run.started_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "summary": run.summary,
            }
            if run
            else None
        }
    return status


@router.get("/runs")
async def list_runs(db: DBSession, agent_name: str | None = None, limit: int = 20):
    q = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if agent_name:
        q = q.where(AgentRun.agent_name == agent_name)
    result = await db.execute(q)
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "agent_name": r.agent_name,
            "status": r.status,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_ms": r.duration_ms,
            "summary": r.summary,
        }
        for r in runs
    ]


@router.post("/{agent_name}/trigger")
async def trigger_agent(agent_name: str, db: DBSession):
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    from cbrain.agents.base import get_agent

    agent = get_agent(agent_name)
    run = await agent.run(db)
    return {
        "run_id": str(run.id),
        "agent_name": agent_name,
        "status": run.status,
        "summary": run.summary,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": str(run.id),
        "agent_name": run.agent_name,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_ms": run.duration_ms,
        "summary": run.summary,
        "actions_taken": run.actions_taken,
        "errors": run.errors,
    }
