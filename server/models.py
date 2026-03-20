"""Pydantic models for TARS request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TarsRequest(BaseModel):
    """Incoming request from the iOS client."""

    message: str = Field(..., min_length=1, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class ConfirmRequest(BaseModel):
    """Confirmation for a sensitive action."""

    action_id: str
    confirmed: bool


class LLMPlan(BaseModel):
    """Structured plan returned by the reasoning LLM."""

    intent: str
    target: str | None = None
    steps: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    parameters: dict[str, Any] = Field(default_factory=dict)
    response: str = ""


class ActionResult(BaseModel):
    """Result of executing an action."""

    success: bool
    output: str = ""
    error: str | None = None


class TarsResponse(BaseModel):
    """Response sent back to the iOS client."""

    status: str = "success"
    response: str
    data: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    action_id: str | None = None
    logs: list[str] | None = None
