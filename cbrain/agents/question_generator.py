from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.agents.base import AgentRunResult, BaseAgent
from cbrain.services.question_engine import generate_questions


class QuestionGeneratorAgent(BaseAgent):
    name = "question_generator"

    async def execute(self, db: AsyncSession) -> AgentRunResult:
        """Generate clarifying questions from context gaps."""
        questions = await generate_questions(db, max_questions=5)
        return AgentRunResult(
            summary=f"Generated {len(questions)} new questions.",
            actions=[
                {"type": "question_created", "question": q.question_text}
                for q in questions
            ],
        )
