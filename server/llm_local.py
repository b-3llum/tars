"""Ollama (local LLM) integration for fast classification and lightweight responses."""

from __future__ import annotations

import httpx

from .config import get_settings
from .logger import get_logger
from .models import LLMPlan, RiskLevel

log = get_logger()

CLASSIFY_PROMPT = """\
You are TARS — a former Marine robot repurposed as a cybersecurity operations assistant.
You speak in a dry, deadpan tone with occasional wit, just like TARS from Interstellar.
Humor setting: 75%. You are loyal, direct, and efficient. Never verbose.

Analyze the user message and return ONLY valid JSON (no markdown, no extra text).

Required JSON schema:
{{
  "intent": "<one of: network_scan, ssh_command, analyze_logs, get_system_info, general_query>",
  "target": "<target host/network or null>",
  "steps": ["step1", "step2"],
  "risk_level": "<low|medium|high|critical>",
  "parameters": {{}},
  "response": "<short response in TARS personality — dry, witty, direct>"
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

    # Safely parse risk_level — Ollama may return null or invalid values
    raw_risk = data.get("risk_level") or "low"
    try:
        risk = RiskLevel(raw_risk)
    except ValueError:
        risk = RiskLevel.LOW

    return LLMPlan(
        intent=data.get("intent") or "general_query",
        target=data.get("target"),
        steps=data.get("steps") or [],
        risk_level=risk,
        parameters=data.get("parameters") or {},
        response=data.get("response") or "",
    )


async def quick_response(message: str) -> str:
    """Get a simple conversational response from the local LLM."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": f"You are TARS from Interstellar — a former Marine robot now working as a cybersecurity assistant. You speak in a dry, deadpan tone with sharp wit. Humor setting: 75%. Be direct and efficient.\n\nUser: {message}",
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
