"""Action engine — executes plans using predefined safe command mappings."""

from __future__ import annotations

import asyncio
import re
import subprocess
import uuid

from .config import get_tars_config
from .logger import audit, get_logger
from .models import ActionResult, LLMPlan
from .security import sanitize_input, validate_target
from .ssh_manager import SSHError, execute_on_host

log = get_logger()

# Pending actions awaiting confirmation: action_id -> LLMPlan
_pending_confirmations: dict[str, LLMPlan] = {}


def requires_confirmation(plan: LLMPlan) -> bool:
    """Check if this action needs explicit user confirmation."""
    config = get_tars_config()
    sensitive = config.get("sensitive_actions", [])
    return plan.intent in sensitive or plan.risk_level in ("high", "critical")


def store_pending(plan: LLMPlan) -> str:
    """Store a plan pending confirmation and return its action_id."""
    action_id = uuid.uuid4().hex[:12]
    _pending_confirmations[action_id] = plan
    return action_id


def pop_pending(action_id: str) -> LLMPlan | None:
    """Retrieve and remove a pending plan."""
    return _pending_confirmations.pop(action_id, None)


def _resolve_command(template: str, params: dict[str, str]) -> str:
    """Safely fill a whitelisted command template with sanitized parameters."""
    resolved = template
    for key, value in params.items():
        safe_value = sanitize_input(str(value))
        resolved = resolved.replace(f"{{{key}}}", safe_value)
    # Reject if any unfilled placeholders remain
    if re.search(r"\{[a-z_]+\}", resolved):
        raise ValueError(f"Unresolved placeholders in command: {resolved}")
    return resolved


def _run_local(command: str, timeout: int = 60) -> str:
    """Run a whitelisted command locally."""
    log.info("Executing local command: %s", command)
    audit("local_exec", detail=command)

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip()
        log.warning("Command exited %d: %s", result.returncode, err)
        output = f"{output}\n[stderr] {err}".strip()

    return output


async def execute(plan: LLMPlan) -> ActionResult:
    """Execute a plan by mapping intents to safe, predefined actions."""
    config = get_tars_config()
    whitelist = config.get("command_whitelist", {})

    audit(
        "action_start",
        intent=plan.intent,
        target=plan.target,
        risk=plan.risk_level,
    )

    try:
        match plan.intent:
            case "network_scan":
                return await _handle_network_scan(plan, whitelist)
            case "get_system_info":
                return await _handle_system_info(plan, whitelist)
            case "analyze_logs":
                return await _handle_log_analysis(plan, whitelist)
            case "ssh_command":
                return await _handle_ssh(plan, whitelist)
            case "general_query":
                return ActionResult(success=True, output=plan.response)
            case _:
                audit("action_rejected", intent=plan.intent, result="unknown_intent")
                return ActionResult(
                    success=False,
                    error=f"Unknown intent: {plan.intent}",
                )
    except Exception as e:
        log.exception("Action execution failed")
        audit("action_error", intent=plan.intent, detail=str(e))
        return ActionResult(success=False, error=str(e))


async def _handle_network_scan(plan: LLMPlan, whitelist: dict) -> ActionResult:
    target = plan.target or plan.parameters.get("target", "")
    if not target or not validate_target(target):
        return ActionResult(success=False, error=f"Invalid scan target: {target}")

    templates = whitelist.get("network_scan", [])
    if not templates:
        return ActionResult(success=False, error="No scan commands configured")

    # Use first template (basic discovery) by default
    cmd = _resolve_command(templates[0], {"target": target})
    output = await asyncio.to_thread(_run_local, cmd)

    audit("action_complete", intent="network_scan", target=target, result="ok")
    return ActionResult(success=True, output=output)


async def _handle_system_info(plan: LLMPlan, whitelist: dict) -> ActionResult:
    templates = whitelist.get("system_info", [])
    if not templates:
        return ActionResult(success=False, error="No system_info commands configured")

    outputs = []
    for tmpl in templates:
        try:
            cmd = _resolve_command(tmpl, {})
            out = await asyncio.to_thread(_run_local, cmd, 15)
            outputs.append(out)
        except Exception as e:
            outputs.append(f"[error] {e}")

    audit("action_complete", intent="get_system_info", result="ok")
    return ActionResult(success=True, output="\n---\n".join(outputs))


async def _handle_log_analysis(plan: LLMPlan, whitelist: dict) -> ActionResult:
    templates = whitelist.get("log_analysis", [])
    if not templates:
        return ActionResult(success=False, error="No log_analysis commands configured")

    params = {
        "lines": str(plan.parameters.get("lines", 100)),
        "logfile": sanitize_input(plan.parameters.get("logfile", "/var/log/syslog")),
        "pattern": sanitize_input(plan.parameters.get("pattern", "error")),
        "service": sanitize_input(plan.parameters.get("service", "")),
        "since": sanitize_input(plan.parameters.get("since", "1 hour ago")),
    }

    cmd = _resolve_command(templates[0], params)
    output = await asyncio.to_thread(_run_local, cmd)

    audit("action_complete", intent="analyze_logs", result="ok")
    return ActionResult(success=True, output=output)


async def _handle_ssh(plan: LLMPlan, whitelist: dict) -> ActionResult:
    host_name = plan.parameters.get("host")
    command = plan.parameters.get("command", "")

    if not host_name:
        return ActionResult(success=False, error="No SSH host specified in parameters")
    if not command:
        return ActionResult(success=False, error="No SSH command specified")

    # Ensure the command matches a whitelisted pattern
    all_templates = []
    for templates in whitelist.values():
        all_templates.extend(templates)

    command_safe = sanitize_input(command)
    # Basic check: the command root should appear in at least one template
    cmd_root = command_safe.split()[0] if command_safe else ""
    allowed_roots = {t.split()[0] for t in all_templates}
    if cmd_root not in allowed_roots:
        audit("action_rejected", intent="ssh_command", detail=f"blocked: {cmd_root}")
        return ActionResult(
            success=False,
            error=f"Command '{cmd_root}' is not in the whitelist",
        )

    try:
        output = await asyncio.to_thread(execute_on_host, host_name, command_safe)
    except SSHError as e:
        return ActionResult(success=False, error=str(e))

    audit("action_complete", intent="ssh_command", target=host_name, result="ok")
    return ActionResult(success=True, output=output)
