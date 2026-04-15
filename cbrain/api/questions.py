from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cbrain.db.models import Question
from cbrain.deps import DBSession

router = APIRouter()


class AnswerBody(BaseModel):
    answer_text: str


@router.get("")
async def list_questions(db: DBSession, status: str = "pending", limit: int = 10):
    q = (
        select(Question)
        .where(Question.status == status)
        .order_by(Question.priority.asc())
        .limit(limit)
    )
    result = await db.execute(q)
    questions = result.scalars().all()
    return [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "context": q.context,
            "generated_by": q.generated_by,
            "priority": q.priority,
            "status": q.status,
            "created_at": q.created_at.isoformat(),
        }
        for q in questions
    ]


@router.get("/{question_id}")
async def get_question(question_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return {
        "id": str(question.id),
        "question_text": question.question_text,
        "context": question.context,
        "generated_by": question.generated_by,
        "priority": question.priority,
        "status": question.status,
        "answer_text": question.answer_text,
        "answered_at": question.answered_at.isoformat() if question.answered_at else None,
        "created_at": question.created_at.isoformat(),
    }


@router.post("/{question_id}/answer")
async def answer_question(question_id: uuid.UUID, body: AnswerBody, db: DBSession):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.answer_text = body.answer_text
    question.answered_at = datetime.now()
    question.status = "answered"
    await db.commit()
    return {"id": str(question.id), "status": "answered"}


@router.post("/{question_id}/dismiss")
async def dismiss_question(question_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.status = "dismissed"
    await db.commit()
    return {"id": str(question.id), "status": "dismissed"}
