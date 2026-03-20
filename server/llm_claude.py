"""Anthropic Claude integration for advanced reasoning and planning."""

from __future__ import annotations

import json

import anthropic

from .config import get_settings
from .logger import get_logger
from .models import LLMPlan, RiskLevel

log = get_logger()

SYSTEM_PROMPT = """\
You are TARS, an advanced AI assistant specialized in cybersecurity operations.
You help the operator plan and execute security tasks on their authorized lab environment.

RULES:
- Only suggest actions against explicitly authorized targets.
- Always assess risk level honestly.
- Return ONLY valid JSON matching the required schema — no markdown fences, no extra text.

Required JSON schema:
{
  "intent": "<network_scan|ssh_command|analyze_logs|get_system_info|general_query>",
  "target": "<target or null>",
  "steps": ["step1", "step2"],
  "risk_level": "<low|medium|high|critical>",
  "parameters": {},
  "response": "<human-readable explanation>"
}
"""


async def reason_and_plan(message: str, context: dict | None = None) -> LLMPlan:
    """Use Claude for complex reasoning and structured plan generation."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    user_content = message
    if context:
        user_content += f"\n\nAdditional context: {json.dumps(context)}"

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    log.debug("Claude raw response: %s", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Claude returned non-JSON: %s", raw[:200])
        return LLMPlan(intent="general_query", response=raw)

    return LLMPlan(
        intent=data.get("intent", "general_query"),
        target=data.get("target"),
        steps=data.get("steps", []),
        risk_level=RiskLevel(data.get("risk_level", "low")),
        parameters=data.get("parameters", {}),
        response=data.get("response", ""),
    )


async def summarize(text: str) -> str:
    """Use Claude to summarize action results."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"Summarize this cybersecurity tool output concisely:\n\n{text[:4000]}",
            }
        ],
    )

    return response.content[0].text.strip()
