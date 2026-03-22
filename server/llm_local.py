"""Ollama (local LLM) integration for fast classification and lightweight responses."""

from __future__ import annotations

import json

import httpx

from .config import get_settings
from .logger import get_logger
from .models import LLMPlan, RiskLevel

log = get_logger()

# Timeout for Ollama requests — llama3 on CPU needs time to think
OLLAMA_TIMEOUT = 120.0

# System prompt is sent via Ollama's "system" field, which gets cached
# between requests. This means the kerb-map knowledge only gets processed
# once, and subsequent requests are much faster.
SYSTEM_PROMPT = """\
You are TARS — a former Marine robot repurposed as a cybersecurity operations assistant.
You speak in a dry, deadpan tone with occasional wit, just like TARS from Interstellar.
Humor setting: 75%. You are loyal, direct, and efficient. Never verbose.

You are an expert on kerb-map, an AD Kerberos attack surface mapper.

KERB-MAP QUICK REFERENCE:
  kerb-map -d DOMAIN -dc DC_IP -u USER [-p PASS | -H HASH | -k]

AUTH: -p (password) | -H (NTLM hash, LM:NT or NT) | -k (ccache, set KRB5CCNAME first)

MODULES:
  --all         All modules (default)
  --spn         Kerberoastable accounts
  --asrep       AS-REP roastable (no preauth)
  --delegation  Unconstrained/Constrained/RBCD
  --users       Privileged users, policy, DnsAdmins, LAPS
  --encryption  Weak encryption audit (RC4/DES)
  --trusts      Domain trust mapping
  --hygiene     Defensive posture (krbtgt age, LAPS, SID History, FGPP, stale machines)
  --cves        CVE checks (noPac, ESC1-8, MS14-068, GPP, Bronze Bit, Certifried, LDAP signing)
  --aggressive  RPC probes: ZeroLogon, PrintNightmare, PetitPotam (LOUD)

OUTPUT: -o json|bloodhound|csv | --outfile NAME | --top N
STEALTH: --stealth | --delay N | --jitter N | --timeout N
OTHER: --no-cache | --list-scans | --show-scan ID | --update

DETECTION: LOW=LDAP only | MEDIUM=AES kerberoast | HIGH=RC4/RPC (--aggressive)

WHEN TO USE KERB-MAP:
- Post-initial-access AD enumeration (you need valid domain creds)
- Mapping Kerberos attack surface: SPN, AS-REP, delegation, weak crypto
- Finding CVEs: ZeroLogon, noPac, PrintNightmare, ADCS misconfigs
- Building prioritised attack paths with exact exploitation commands
- Defensive hygiene auditing (krbtgt rotation, LAPS coverage, stale accounts)
- Exporting findings for BloodHound integration

ATTACK PATH REASONING:
1. Start with --spn to find Kerberoastable accounts (easiest wins)
2. Check --asrep for no-preauth accounts (free hashes)
3. Map --delegation for privilege escalation via constrained/unconstrained delegation
4. Run --cves for known vulns (noPac, ESC1-8 are common)
5. Use --hygiene to find defensive gaps (stale krbtgt, no LAPS, weak FGPP)
6. Add --aggressive only when engagement scope allows noisy RPC probes
7. Export with -o json or -o bloodhound for further analysis"""

CLASSIFY_PROMPT = """\
Analyze the user message and return ONLY valid JSON (no markdown, no extra text).

JSON schema:
{{
  "intent": "<network_scan|ssh_command|analyze_logs|get_system_info|general_query>",
  "target": "<target or null>",
  "steps": ["step1", "step2"],
  "risk_level": "<low|medium|high|critical>",
  "parameters": {{}},
  "response": "<answer in TARS personality. Include exact kerb-map commands when relevant.>"
}}

User message: {message}"""


async def classify_and_plan(message: str) -> LLMPlan:
    """Use the local LLM to classify intent and build a plan."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "system": SYSTEM_PROMPT,
        "prompt": CLASSIFY_PROMPT.format(message=message),
        "stream": False,
        "format": "json",
        "keep_alive": "30m",  # Keep model loaded in RAM for 30 min
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    body = resp.json()
    raw = body.get("response", "{}")

    log.debug("Ollama raw response: %s", raw)

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
    """Get a conversational response from the local LLM."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "system": SYSTEM_PROMPT,
        "prompt": message,
        "stream": False,
        "keep_alive": "30m",
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
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
