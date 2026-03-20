"""Audit logging for TARS — every action gets recorded."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Structured audit log (JSON lines)
_audit_path = LOG_DIR / "audit.jsonl"

# Standard application logger
_logger = logging.getLogger("tars")
_logger.setLevel(logging.DEBUG)

_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s"))
_logger.addHandler(_console)

_file_handler = logging.FileHandler(LOG_DIR / "tars.log")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s %(name)s — %(message)s")
)
_logger.addHandler(_file_handler)


def get_logger() -> logging.Logger:
    return _logger


def audit(
    event: str,
    *,
    intent: str | None = None,
    target: str | None = None,
    risk: str | None = None,
    result: str | None = None,
    detail: str | None = None,
) -> None:
    """Append a structured audit entry."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "intent": intent,
        "target": target,
        "risk": risk,
        "result": result,
        "detail": detail,
    }
    # Drop None values for cleaner logs
    entry = {k: v for k, v in entry.items() if v is not None}
    with open(_audit_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _logger.info("AUDIT | %s | intent=%s target=%s", event, intent, target)
