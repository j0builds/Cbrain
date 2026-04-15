from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from cbrain.db.engine import async_session

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_agent(agent_name: str):
    """Wrapper to run an agent within a DB session."""
    from cbrain.agents.base import get_agent

    logger.info(f"[scheduler] Starting agent: {agent_name}")
    agent = get_agent(agent_name)
    async with async_session() as db:
        run = await agent.run(db)
        logger.info(f"[scheduler] Agent {agent_name} finished: {run.status} — {run.summary}")


AGENT_SCHEDULE = {
    "consolidator": CronTrigger(hour=3, minute=0),
    "enricher": CronTrigger(hour=4, minute=0),
    "prioritizer": CronTrigger(hour=5, minute=0),
    "question_generator": CronTrigger(hour=5, minute=30),
}


async def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler()

    for agent_name, trigger in AGENT_SCHEDULE.items():
        _scheduler.add_job(
            _run_agent,
            trigger=trigger,
            args=[agent_name],
            id=f"agent_{agent_name}",
            name=f"C-Brain Agent: {agent_name}",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info("[scheduler] Started with %d jobs", len(AGENT_SCHEDULE))


async def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped")
