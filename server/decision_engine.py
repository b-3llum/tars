"""Decision engine — all requests route through Ollama (local LLM)."""

from __future__ import annotations

from .logger import audit, get_logger
from .models import LLMPlan, TarsRequest

log = get_logger()


async def route_request(request: TarsRequest) -> LLMPlan:
    """Route all requests through the local Ollama LLM."""
    from . import llm_local

    message = request.message

    log.info("Routing to local LLM (Ollama)")
    audit("route_decision", detail="local_llm")

    if not await llm_local.is_available():
        log.error("Ollama is not available")
        return LLMPlan(
            intent="general_query",
            response="Ollama is offline. I cannot process your request. Check that 'ollama serve' is running.",
        )

    return await llm_local.classify_and_plan(message)
