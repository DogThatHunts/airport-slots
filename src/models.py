"""Model routing.

The pipeline tags each LLM task with a capability *tier*. Routine, high-volume
work (parsing, normalization, field extraction) goes to the cheap tier so we burn
as few tokens as possible; only genuine ambiguity/anomaly reasoning uses a stronger
model. Phone escalation itself is handled by the Claude Code routine, not here.

Set ANTHROPIC_API_KEY in the environment (or .env) for headless runs.
"""
from __future__ import annotations

import os

# Tier -> model id. Keep routine work on Haiku.
TIERS = {
    "cheap": "claude-haiku-4-5-20251001",   # normalization, extraction, diffs
    "smart": "claude-sonnet-4-6",           # ambiguous parses, anomaly summaries
}

DEFAULT_TIER = "cheap"


def complete(prompt: str, *, tier: str = DEFAULT_TIER, system: str | None = None,
             max_tokens: int = 1024) -> str:
    """Single-shot completion at the given tier. Returns the text.

    Kept deliberately thin so the pipeline can call it in tight loops. Swap the
    body to route to a non-Claude provider per-tier if desired later.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=TIERS.get(tier, TIERS[DEFAULT_TIER]),
        max_tokens=max_tokens,
        system=system or "You are a precise data-extraction assistant. Return only what is asked.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
