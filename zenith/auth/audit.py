"""
Structured audit events for security-relevant actions.

Logs use structlog JSON; never include tokens, refresh tokens, or raw OAuth codes.
"""
from typing import Any

import structlog

logger = structlog.get_logger()

_SENSITIVE_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "password",
        "secret",
        "client_secret",
        "credentials",
    }
)


def log_audit_event(event: str, **fields: Any) -> None:
    """
    Emit a single audit line with event name and safe fields.

    Strips known sensitive keys from accidental inclusion.
    """
    safe = {k: v for k, v in fields.items() if k.lower() not in _SENSITIVE_KEYS}
    logger.info("audit", audit_event=event, **safe)
