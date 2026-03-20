"""Security utilities — auth, validation, rate limiting."""

from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from .config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key")

# In-memory rate limiter (per IP)
_request_times: dict[str, list[float]] = defaultdict(list)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """Validate the API key from the request header."""
    expected = get_settings().tars_api_key
    # Constant-time comparison via hash
    if hashlib.sha256(api_key.encode()).digest() != hashlib.sha256(expected.encode()).digest():
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def rate_limit(request: Request) -> None:
    """Enforce per-IP rate limiting."""
    rpm = get_settings().rate_limit_rpm
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0

    # Prune old entries
    _request_times[client_ip] = [
        t for t in _request_times[client_ip] if now - t < window
    ]

    if len(_request_times[client_ip]) >= rpm:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    _request_times[client_ip].append(now)


# --- Input sanitization ---

_DANGEROUS_PATTERNS = [
    r"[;&|`$]",        # shell metacharacters
    r"\.\./",          # path traversal
    r"rm\s+-rf",       # destructive commands
    r">(>)?",          # redirects
    r"\$\(",           # command substitution
]

_DANGEROUS_RE = re.compile("|".join(_DANGEROUS_PATTERNS))


def sanitize_input(text: str) -> str:
    """Strip dangerous shell patterns from user input."""
    return _DANGEROUS_RE.sub("", text).strip()


def validate_target(target: str) -> bool:
    """Validate that a target looks like a hostname, IP, or CIDR."""
    ip_re = re.compile(
        r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$"  # IPv4 / CIDR
        r"|^[a-zA-Z0-9._-]+$"                     # hostname
    )
    return bool(ip_re.match(target))
