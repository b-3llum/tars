"""Ollama (local LLM) integration for fast classification and lightweight responses."""

from __future__ import annotations

import httpx

from .config import get_settings
from .logger import get_logger
from .models import LLMPlan, RiskLevel

log = get_logger()

CLASSIFY_PROMPT = """\
You are TARS, a cybersecurity assistant. Analyze the user message and return ONLY valid JSON.

Required JSON schema:
{{
  "intent": "<one of: network_scan, ssh_command, analyze_logs, get_system_info, general_query>",
  "target": "<target host/network or null>",
  "steps": ["step1", "step2"],
  "risk_level": "<low|medium|high|critical>",
  "parameters": {{}},
  "response": "<short human-readable response>"
}}

User message: {message}
"""


async def classify_and_plan(message: str) -> LLMPlan:
    """Use the local LLM to classify intent and build a lightweight plan."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": CLASSIFY_PROMPT.format(message=message),
        "stream": False,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    body = resp.json()
    raw = body.get("response", "{}")

    log.debug("Ollama raw response: %s", raw)

    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Ollama returned non-JSON; falling back to general_query")
        return LLMPlan(
            intent="general_query",
            response="I can help with that. Could you be more specific?",
        )

    return LLMPlan(
        intent=data.get("intent", "general_query"),
        target=data.get("target"),
        steps=data.get("steps", []),
        risk_level=RiskLevel(data.get("risk_level", "low")),
        parameters=data.get("parameters", {}),
        response=data.get("response", ""),
    )


async def quick_response(message: str) -> str:
    """Get a simple conversational response from the local LLM."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": f"You are TARS, a concise cybersecurity assistant. Respond briefly.\n\nUser: {message}",
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    return resp.json().get("response", "")


async def is_available() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{get_settings().ollama_base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
