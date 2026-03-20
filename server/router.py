"""API router — all TARS endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from . import action_engine, decision_engine, llm_local
from .logger import audit, get_logger
from .models import ConfirmRequest, TarsRequest, TarsResponse
from .security import rate_limit, verify_api_key

log = get_logger()

router = APIRouter(prefix="/tars", dependencies=[Depends(verify_api_key)])


@router.get("/health")
async def health():
    ollama_ok = await llm_local.is_available()
    return {
        "status": "online",
        "ollama": "available" if ollama_ok else "unavailable",
        "version": "1.0.0",
    }


@router.post("/request", response_model=TarsResponse)
async def handle_request(body: TarsRequest, request: Request):
    rate_limit(request)

    audit("request_received", detail=body.message[:120])

    # 1. Route to the right LLM and get a plan
    plan = await decision_engine.route_request(body)

    # 2. Check if confirmation is needed
    if action_engine.requires_confirmation(plan):
        action_id = action_engine.store_pending(plan)
        audit("confirmation_required", intent=plan.intent, detail=action_id)
        return TarsResponse(
            status="pending_confirmation",
            response=f"{plan.response}\n\nThis action requires your confirmation before execution.",
            data={"plan": plan.model_dump()},
            requires_confirmation=True,
            action_id=action_id,
        )

    # 3. Execute the action
    result = await action_engine.execute(plan)

    return TarsResponse(
        status="success" if result.success else "error",
        response=plan.response if result.success else (result.error or "Action failed"),
        data={"output": result.output} if result.output else {},
    )


@router.post("/confirm", response_model=TarsResponse)
async def confirm_action(body: ConfirmRequest, request: Request):
    rate_limit(request)

    plan = action_engine.pop_pending(body.action_id)

    if plan is None:
        return TarsResponse(
            status="error",
            response="No pending action found with that ID. It may have expired.",
        )

    if not body.confirmed:
        audit("action_cancelled", intent=plan.intent, detail=body.action_id)
        return TarsResponse(
            status="cancelled",
            response="Action cancelled.",
        )

    audit("action_confirmed", intent=plan.intent, detail=body.action_id)

    result = await action_engine.execute(plan)

    return TarsResponse(
        status="success" if result.success else "error",
        response=plan.response if result.success else (result.error or "Action failed"),
        data={"output": result.output} if result.output else {},
    )
