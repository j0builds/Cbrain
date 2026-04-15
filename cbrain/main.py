from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cbrain.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load skills, start scheduler
    from cbrain.agents.scheduler import start_scheduler, stop_scheduler

    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()


app = FastAPI(
    title="C-Brain",
    description="Enterprise Brain MVP — CEO-prioritized task intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/v1/health")
async def health():
    from sqlalchemy import text

    from cbrain.db.engine import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        result.scalar()
    return {"status": "ok", "service": "cbrain"}
