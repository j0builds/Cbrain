from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import frontmatter
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import Skill, SkillExecution
from cbrain.services.claude_client import ask_claude
from cbrain.services.context_store import hybrid_search


async def execute_skill(
    db: AsyncSession,
    skill: Skill,
    input_data: dict,
    triggered_by: str = "user",
) -> SkillExecution:
    """Execute a skill by assembling its markdown + brain context into a Claude prompt."""
    execution = SkillExecution(
        skill_id=skill.id,
        input_data=input_data,
        status="running",
        triggered_by=triggered_by,
    )
    db.add(execution)
    await db.flush()

    try:
        # Read skill markdown
        skill_path = Path(skill.markdown_path)
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {skill.markdown_path}")

        post = frontmatter.load(str(skill_path))
        skill_instructions = post.content

        # Gather relevant context from brain
        search_query = input_data.get("focus_area", skill.display_name)
        context_results = await hybrid_search(db, search_query, limit=10)

        context_block = "\n\n".join([
            f"### {r['title']} ({r['entry_type']}, {r['importance_tier']})\n{r['body']}"
            for r in context_results
        ]) if context_results else "No relevant context found in brain."

        # Assemble prompt
        system = f"""You are a skill executor for C-Brain, an enterprise knowledge system.

## Skill Instructions
{skill_instructions}

## Brain Context (relevant entries)
{context_block}"""

        prompt = f"Input data:\n```json\n{json.dumps(input_data, indent=2)}\n```\n\nExecute the skill and return the result."

        # Call Claude
        response = await ask_claude(
            prompt,
            system=system,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
        )

        execution.output_text = response.text
        execution.status = "completed"
        execution.model = response.model
        execution.tokens_input = response.input_tokens
        execution.tokens_output = response.output_tokens
        execution.duration_ms = response.duration_ms

        # Update skill stats
        skill.execution_count += 1
        skill.last_executed_at = datetime.now()

    except Exception as e:
        execution.status = "failed"
        execution.error_message = str(e)

    await db.commit()
    await db.refresh(execution)
    return execution
