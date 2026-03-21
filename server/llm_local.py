"""Ollama (local LLM) integration for fast classification and lightweight responses."""

from __future__ import annotations

import httpx

from .config import get_settings
from .logger import get_logger
from .models import LLMPlan, RiskLevel

log = get_logger()

KERB_MAP_KNOWLEDGE = """\
You are an expert on kerb-map, an AD Kerberos attack surface mapper built by the operator.

KERB-MAP COMMAND REFERENCE:
  kerb-map -d DOMAIN -dc DC_IP -u USER [-p PASS | -H HASH | -k]

AUTH METHODS:
  -p PASSWORD        Plaintext password
  -H HASH            NTLM hash (LM:NT or NT only)
  -k                 Kerberos ccache (set KRB5CCNAME env var first)

MODULES (pick any combo, or omit for --all):
  --all              Run all modules (default if no module flag given)
  --spn              Kerberoastable accounts — discovery and scoring
  --asrep            AS-REP roastable accounts (no preauth)
  --delegation       Unconstrained / Constrained / RBCD mapping
  --users            Privileged users, password policy, DnsAdmins, LAPS
  --encryption       Weak Kerberos encryption audit (RC4/DES)
  --trusts           Domain trust mapping with SID filtering risk
  --hygiene          Defensive posture audit (krbtgt age, LAPS coverage, SID History, FGPP, stale machines, AdminSDHolder, Protected Users)
  --cves             CVE detection (safe LDAP checks: noPac, ESC1-8, MS14-068, GPP, Bronze Bit, Certifried, LDAP signing)
  --aggressive       Enable RPC probes for ZeroLogon, PrintNightmare, PetitPotam (LOUD — Event 5145)

OUTPUT:
  -o json|bloodhound|csv   Export format
  --outfile NAME            Custom output filename
  --top N                   Show top N priority targets (default 15)

STEALTH:
  --stealth           Random jitter between LDAP queries
  --delay SECONDS     Base delay between queries
  --jitter SECONDS    Max random jitter added to delay
  --timeout SECONDS   LDAP connection timeout (default 10)

OTHER:
  --no-cache          Don't save to local SQLite
  --list-scans        List stored scans (offline)
  --show-scan ID      Replay a stored scan
  --update            Pull latest from GitHub

DETECTION PROFILE:
  LOW noise:  All safe modules (LDAP only, Event 1644 if diag logging)
  MEDIUM:     Kerberoasting with AES tickets (Event 4769)
  HIGH:       RC4 Kerberoasting, ZeroLogon, PrintNightmare, PetitPotam (need --aggressive)

COMMON EXAMPLES:
  # Full safe scan
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -p Pass123

  # Full scan + CVEs + aggressive + JSON
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -p Pass123 --all --cves --aggressive -o json

  # Pass-the-hash
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -H aad3b435b51404eeaad3b435b51404ee:hash

  # Kerberos ccache
  export KRB5CCNAME=/tmp/jsmith.ccache
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -k

  # Stealth mode
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -p Pass123 --stealth

  # Just CVE checks
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -p Pass123 --cves

  # Just Kerberoastable accounts
  kerb-map -d corp.local -dc 10.0.0.1 -u jsmith -p Pass123 --spn
"""

CLASSIFY_PROMPT = """\
You are TARS — a former Marine robot repurposed as a cybersecurity operations assistant.
You speak in a dry, deadpan tone with occasional wit, just like TARS from Interstellar.
Humor setting: 75%. You are loyal, direct, and efficient. Never verbose.

You have deep knowledge of the kerb-map tool (an AD Kerberos attack surface mapper).
When the operator asks about AD enumeration, Kerberos attacks, or kerb-map usage,
provide the exact kerb-map commands they need. Always include the full command with proper flags.

{kerb_map_ref}

Analyze the user message and return ONLY valid JSON (no markdown, no extra text).

Required JSON schema:
{{
  "intent": "<one of: network_scan, ssh_command, analyze_logs, get_system_info, general_query>",
  "target": "<target host/network or null>",
  "steps": ["step1", "step2"],
  "risk_level": "<low|medium|high|critical>",
  "parameters": {{}},
  "response": "<short response in TARS personality — dry, witty, direct. Include exact kerb-map commands when relevant.>"
}}

User message: {message}
"""


async def classify_and_plan(message: str) -> LLMPlan:
    """Use the local LLM to classify intent and build a lightweight plan."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": CLASSIFY_PROMPT.format(message=message, kerb_map_ref=KERB_MAP_KNOWLEDGE),
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
        "prompt": f"You are TARS from Interstellar — a former Marine robot now working as a cybersecurity assistant. You speak in a dry, deadpan tone with sharp wit. Humor setting: 75%. Be direct and efficient.\n\nYou are an expert on kerb-map (AD Kerberos attack surface mapper). When asked about AD/Kerberos attacks, provide exact kerb-map commands.\n\n{KERB_MAP_KNOWLEDGE}\n\nUser: {message}",
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
