from __future__ import annotations

from fastapi import APIRouter

from cbrain.api import context, dashboard, questions, skills, sync, tasks

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(context.router, prefix="/context", tags=["context"])
api_router.include_router(sync.router, tags=["sync"])
