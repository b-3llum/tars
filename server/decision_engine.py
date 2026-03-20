"""Decision engine — routes requests to local LLM or Claude based on complexity."""

from __future__ import annotations

import re

from .config import get_tars_config
from .logger import audit, get_logger
from .models import LLMPlan, TarsRequest

log = get_logger()


def is_simple_task(message: str) -> bool:
    """Determine if a message can be handled by the local LLM.

    A task is simple if:
    - It's short (under 80 chars)
    - It matches a known simple intent keyword
    - It contains no complex multi-step language
    """
    config = get_tars_config()
    simple_intents = config.get("simple_intents", [])

    # Long messages are probably complex
    if len(message) > 80:
        return False

    lower = message.lower()

    # Check for complexity signals
    complex_signals = ["plan", "analyze", "explain", "compare", "investigate", "why", "how does"]
    if any(s in lower for s in complex_signals):
        return False

    # Check for known simple intents
    words = re.findall(r"\w+", lower)
    if any(word in simple_intents for word in words):
        return True

    # Default: treat as complex
    return False


async def route_request(request: TarsRequest) -> LLMPlan:
    """Decide which LLM to use and return a structured plan."""
    from . import llm_claude, llm_local

    message = request.message

    if is_simple_task(message):
        log.info("Routing to local LLM (simple task)")
        audit("route_decision", detail="local_llm")

        if await llm_local.is_available():
            return await llm_local.classify_and_plan(message)
        else:
            log.warning("Ollama unavailable, falling back to Claude")
            audit("fallback", detail="ollama_unavailable")

    log.info("Routing to Claude (complex task)")
    audit("route_decision", detail="claude")
    return await llm_claude.reason_and_plan(message, request.context)
