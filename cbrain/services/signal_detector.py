from __future__ import annotations

import json
from dataclasses import dataclass, field

from cbrain.services.claude_client import ask_claude


@dataclass
class Signal:
    signal_type: str  # 'entity', 'action_item', 'decision', 'idea'
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    urgency: str = "normal"


async def detect_signals(text: str, source: str = "unknown") -> list[Signal]:
    """Extract entities, action items, decisions, and ideas from text using Claude."""
    if not text.strip():
        return []

    system = """You are a signal detector for C-Brain, an enterprise knowledge system.
Extract structured signals from the input text. Return a JSON array of signals.

Each signal has:
- signal_type: one of "entity", "action_item", "decision", "idea"
- title: short descriptive title (max 100 chars)
- body: detailed description with context
- tags: relevant tags (e.g., person names, project names, topics)
- urgency: "critical", "high", "normal", or "low"

Rules:
- Extract ALL people, companies, and projects mentioned as "entity" signals
- Extract any tasks, to-dos, or follow-ups as "action_item" signals
- Extract any decisions made or pending as "decision" signals
- Extract any ideas, insights, or suggestions as "idea" signals
- Be comprehensive but avoid duplicates
- For action items, include who should do it if mentioned

Return ONLY valid JSON array. No markdown, no explanation."""

    prompt = f"Source: {source}\n\nText to analyze:\n{text}"

    response = await ask_claude(prompt, system=system, max_tokens=2048)

    try:
        # Parse JSON from response
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        signals_data = json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        return []

    signals = []
    for s in signals_data:
        signals.append(Signal(
            signal_type=s.get("signal_type", "idea"),
            title=s.get("title", "Untitled"),
            body=s.get("body", ""),
            tags=s.get("tags", []),
            urgency=s.get("urgency", "normal"),
        ))

    return signals
