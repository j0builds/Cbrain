"""Smart task extraction from brain context entries.
Scores importance, generates descriptions, instructions, and Claude prompts.
No LLM needed — uses brain data structure and pattern analysis."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cbrain.db.models import ContextEntry, Task, TimelineEvent


async def extract_tasks_from_brain(db: AsyncSession) -> dict:
    """Scan all context entries, score importance, generate rich tasks."""

    # Clear old brain-extracted tasks (re-extract fresh each time)
    await db.execute(
        delete(Task).where(Task.source.like("brain:%"))
    )
    await db.flush()

    # Load all entries
    result = await db.execute(select(ContextEntry))
    all_entries = result.scalars().all()

    # Build a cross-reference map: how many times each entry is linked to
    link_counts: dict[str, int] = {}
    for entry in all_entries:
        links = re.findall(r"\[\[([^\]]+)\]\]", entry.body)
        for link in links:
            link_lower = link.lower().strip()
            link_counts[link_lower] = link_counts.get(link_lower, 0) + 1

    candidates: list[_TaskCandidate] = []

    for entry in all_entries:
        # Skip very short entries
        if len(entry.body.strip()) < 50:
            continue

        # Skip historical/completed items
        body_lower = entry.body.lower()
        if _is_archived(body_lower, entry.title.lower()):
            continue

        # Score this entry
        score = _score_entry(entry, link_counts)

        # Only create tasks for entries worth tracking
        if score < 15:
            continue

        # Determine task type from entry
        task_type = _classify_task_type(entry)

        # Generate rich description
        description = _build_description(entry)

        # Generate instructions
        instructions = _build_instructions(entry, task_type, body_lower)

        # Generate Claude prompt
        claude_prompt = _build_claude_prompt(entry, task_type, description)

        # Map score to urgency
        if score >= 70:
            urgency = "critical"
        elif score >= 50:
            urgency = "high"
        elif score >= 30:
            urgency = "normal"
        else:
            urgency = "low"

        candidates.append(_TaskCandidate(
            entry=entry,
            score=score,
            urgency=urgency,
            task_type=task_type,
            description=description,
            instructions=instructions,
            claude_prompt=claude_prompt,
        ))

    # Sort by score, cap at 80
    candidates.sort(key=lambda c: c.score, reverse=True)
    candidates = candidates[:80]

    # Create tasks
    created = 0
    for c in candidates:
        title = c.entry.title
        if c.task_type == "strategy":
            title = f"Execute: {title}"
        elif c.task_type == "entity_review":
            title = f"Review: {title}"

        task = Task(
            title=title,
            description=c.description,
            source=f"brain:{c.task_type}",
            source_id=f"ctx:{c.entry.id}",
            source_hash=hashlib.sha256(f"brain:{c.task_type}:ctx:{c.entry.id}".encode()).hexdigest(),
            urgency=c.urgency,
            importance_score=c.score,
            priority=100 - c.score,  # Higher score = lower priority number = shown first
            priority_reason=_score_reason(c),
            instructions=c.instructions,
            claude_prompt=c.claude_prompt,
            related_context_ids=[c.entry.id],
        )
        db.add(task)
        created += 1

    event = TimelineEvent(
        event_type="task_extraction",
        summary=f"Extracted {created} tasks (scored & ranked from {len(all_entries)} brain entries)",
        source="brain",
        actor="task_extractor",
    )
    db.add(event)
    await db.commit()

    return {"tasks_created": created, "entries_scanned": len(all_entries)}


# ── Scoring ──────────────────────────────────────────────

def _score_entry(entry: ContextEntry, link_counts: dict[str, int]) -> int:
    """Score 0-100 based on multiple signals."""
    score = 0

    # 1. Importance tier (0-40 pts)
    tier_pts = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    score += tier_pts.get(entry.importance_tier, 10)

    # 2. Mention count / inbound links (0-20 pts)
    inbound = link_counts.get(entry.title.lower(), 0)
    total_refs = entry.mention_count + inbound
    if total_refs >= 10:
        score += 20
    elif total_refs >= 5:
        score += 15
    elif total_refs >= 3:
        score += 10
    elif total_refs >= 1:
        score += 5

    # 3. Link density — how connected is this entry (0-15 pts)
    outbound_links = len(re.findall(r"\[\[([^\]]+)\]\]", entry.body))
    if outbound_links >= 10:
        score += 15
    elif outbound_links >= 5:
        score += 10
    elif outbound_links >= 2:
        score += 5

    # 4. Action signals in body (0-15 pts)
    body_lower = entry.body.lower()
    action_signals = [
        "todo", "action item", "next step", "follow up", "need to",
        "deadline", "milestone", "target", "goal", "blocked",
        "pilot", "launch", "ship", "deploy", "pitch", "close",
    ]
    action_hits = sum(1 for s in action_signals if s in body_lower)
    score += min(15, action_hits * 3)

    # 5. Source weight (0-10 pts) — memory items are current priorities
    source_pts = {
        "memory": 10,
        "notion": 8,
        "jopedia": 5,
    }
    score += source_pts.get(entry.source, 3)

    # 6. Entry type weight — projects and decisions are more actionable
    type_bonus = {
        "project": 5,
        "decision": 8,
        "entity": -5,  # Entities are less actionable
        "fact": -10,  # Facts are reference, not tasks
    }
    score += type_bonus.get(entry.entry_type, 0)

    return max(0, min(100, score))


def _is_archived(body_lower: str, title_lower: str) -> bool:
    """Detect entries that are historical/completed."""
    archive_signals = [
        "deprecated", "archived", "sunset", "discontinued",
        "no longer", "was shut down", "was discontinued",
    ]
    return any(s in body_lower for s in archive_signals)


# ── Classification ───────────────────────────────────────

def _classify_task_type(entry: ContextEntry) -> str:
    """Classify what kind of task this entry represents."""
    if entry.entry_type == "project":
        return "project"
    if entry.entry_type == "decision":
        return "decision"
    if entry.entry_type == "entity" and entry.importance_tier in ("high", "critical"):
        return "entity_review"

    tags = entry.tags or []
    if "strategies" in tags:
        return "strategy"
    if "patterns" in tags:
        return "pattern"

    body_lower = entry.body.lower()
    if any(w in body_lower for w in ["todo", "action item", "follow up", "need to"]):
        return "action"

    return "review"


# ── Description ──────────────────────────────────────────

def _build_description(entry: ContextEntry) -> str:
    """Build a rich description from the entry body."""
    parts = []

    # Extract first meaningful paragraph
    for line in entry.body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 30:
            parts.append(line[:300])
            break

    # Extract linked entities
    links = re.findall(r"\[\[([^\]]+)\]\]", entry.body)
    if links:
        unique_links = list(dict.fromkeys(links))[:8]
        parts.append(f"\nConnected to: {', '.join(unique_links)}")

    # Detect status
    body_lower = entry.body.lower()
    if "in progress" in body_lower or "currently" in body_lower:
        parts.append("\nStatus: In progress")
    elif "planned" in body_lower or "will " in body_lower:
        parts.append("\nStatus: Planned")
    elif "shipped" in body_lower or "launched" in body_lower:
        parts.append("\nStatus: Shipped (may need follow-up)")
    elif "stale" in body_lower or "paused" in body_lower:
        parts.append("\nStatus: Stale — needs attention")

    # Source info
    parts.append(f"\nSource: {entry.source} | Type: {entry.entry_type} | Tier: {entry.importance_tier}")

    return "\n".join(parts)


# ── Instructions ─────────────────────────────────────────

_INSTRUCTIONS = {
    "project": [
        "1. Review current project status and recent activity",
        "2. Identify the single biggest blocker or open question",
        "3. Decide the next concrete milestone (ship date, demo, handoff)",
        "4. Assign ownership if not already owned",
        "5. Update the brain with current status",
    ],
    "decision": [
        "1. Review the context and options laid out below",
        "2. Identify what information is missing to decide",
        "3. Set a decision deadline — don't let this rot",
        "4. Make the call or explicitly defer with a reason",
        "5. Record the rationale so the team understands why",
    ],
    "strategy": [
        "1. Assess execution progress — what has been done vs. planned",
        "2. Check if the strategy assumptions still hold",
        "3. Identify gaps in execution — who needs to do what",
        "4. Decide: double down, pivot, or deprioritize",
        "5. Assign concrete next actions with owners",
    ],
    "entity_review": [
        "1. Review what the brain knows about this person/company",
        "2. Check if there's a pending follow-up or conversation",
        "3. Decide: deepen the relationship, maintain, or deprioritize",
        "4. If active — schedule the next touchpoint",
    ],
    "action": [
        "1. Confirm this action item is still relevant",
        "2. Do it or delegate it — no partial credit",
        "3. Update stakeholders on completion",
    ],
    "pattern": [
        "1. Review whether this pattern is being actively applied",
        "2. Identify where it could be applied but isn't",
        "3. Decide if it needs refinement based on recent experience",
    ],
    "review": [
        "1. Read the full brain context for this entry",
        "2. Decide if this needs active work or is reference material",
        "3. If actionable — convert to a specific project or decision",
        "4. If reference — no action needed, dismiss this task",
    ],
}


def _build_instructions(entry: ContextEntry, task_type: str, body_lower: str) -> str:
    """Generate concrete instructions based on task type and content."""
    base = _INSTRUCTIONS.get(task_type, _INSTRUCTIONS["review"])
    lines = list(base)

    # Add content-specific instructions
    if "pitch" in body_lower or "investor" in body_lower:
        lines.append("\nNote: This involves investor relations — prioritize accordingly")
    if "pilot" in body_lower:
        lines.append("\nNote: Active pilot — monitor for results and feedback")
    if "deadline" in body_lower or "due" in body_lower:
        lines.append("\nNote: Time-sensitive — check dates")
    if "blocked" in body_lower:
        lines.append("\nNote: Something is blocked — identify and unblock first")

    return "\n".join(lines)


# ── Claude Prompt ────────────────────────────────────────

_PROMPT_TEMPLATES = {
    "project": """You are my Chief of Staff. Here's a project from my brain:

**{title}**
{context}

Help me with:
1. What's the current state of this project based on the context above?
2. What's the single most important next action?
3. Is anything blocked? If so, what would unblock it?
4. Draft a 3-bullet status update I could share with the team.

Be specific. Reference the actual details, not generic advice.""",

    "decision": """You are my decision advisor. I need to make a call on this:

**{title}**
{context}

Help me think through this:
1. What are the 2-3 realistic options?
2. What's the strongest argument for each?
3. What information am I missing?
4. What would you recommend and why?
5. Is this reversible? What's the cost of being wrong?

Be direct. Give me a recommendation, not just a framework.""",

    "strategy": """You are my strategy advisor. Here's a strategy from my playbook:

**{title}**
{context}

I need you to:
1. Assess whether this strategy still makes sense given current context
2. Identify the biggest execution gap
3. Draft 3 concrete next actions with rough timelines
4. Flag any assumptions that might be wrong

Be specific to my situation. No generic strategy advice.""",

    "entity_review": """You are my relationship advisor. Here's someone/something important in my network:

**{title}**
{context}

Help me with:
1. Summarize what I know about this entity and why it matters
2. Is there a pending action or follow-up I should take?
3. Draft a short message or agenda for the next interaction
4. Rate the relationship: growing / stable / cooling

Be specific to the context above.""",

    "action": """I have an action item that needs completing:

**{title}**
{context}

Help me:
1. Break this into the 2-3 sub-tasks needed to complete it
2. Draft the output (email, document, message — whatever this action requires)
3. Identify if anyone else needs to be looped in

Be concrete. Give me drafts, not outlines.""",
}


def _build_claude_prompt(entry: ContextEntry, task_type: str, description: str) -> str:
    """Generate a ready-to-paste Claude prompt."""
    template = _PROMPT_TEMPLATES.get(task_type, _PROMPT_TEMPLATES["action"])

    # Get relevant body context (first 800 chars)
    context_lines = []
    for line in entry.body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            context_lines.append(line)
        if sum(len(l) for l in context_lines) > 800:
            break
    context = "\n".join(context_lines)

    return template.format(title=entry.title, context=context)


# ── Score Reason ─────────────────────────────────────────

def _score_reason(c: "_TaskCandidate") -> str:
    """Generate a human-readable reason for the importance score."""
    parts = []

    entry = c.entry
    if entry.importance_tier in ("critical", "high"):
        parts.append(f"{entry.importance_tier}-tier in brain")
    if entry.mention_count >= 5:
        parts.append(f"mentioned {entry.mention_count}x")
    if entry.source == "memory":
        parts.append("from active memory")

    outbound = len(re.findall(r"\[\[([^\]]+)\]\]", entry.body))
    if outbound >= 5:
        parts.append(f"connected to {outbound} entities")

    body_lower = entry.body.lower()
    if any(w in body_lower for w in ["blocked", "deadline", "urgent"]):
        parts.append("has urgency signals")
    if any(w in body_lower for w in ["pilot", "launch", "ship"]):
        parts.append("execution-stage")
    if any(w in body_lower for w in ["investor", "pitch", "fundraise"]):
        parts.append("investor-related")

    if not parts:
        parts.append(f"score {c.score} from brain analysis")

    return f"Score {c.score}: {', '.join(parts)}"


# ── Internal types ───────────────────────────────────────

class _TaskCandidate:
    def __init__(self, entry, score, urgency, task_type, description, instructions, claude_prompt):
        self.entry = entry
        self.score = score
        self.urgency = urgency
        self.task_type = task_type
        self.description = description
        self.instructions = instructions
        self.claude_prompt = claude_prompt
