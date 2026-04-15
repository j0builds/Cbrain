from __future__ import annotations

import os
import time
from dataclasses import dataclass

import anthropic

from cbrain.config import settings


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = settings.get_anthropic_key()
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


async def ask_claude(
    prompt: str,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> LLMResponse:
    """Send a prompt to Claude and return structured response with usage tracking."""
    client = get_client()

    messages = [{"role": "user", "content": prompt}]

    start = time.monotonic()
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system if system else anthropic.NOT_GIVEN,
        messages=messages,
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    return LLMResponse(
        text=text,
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        duration_ms=duration_ms,
    )
