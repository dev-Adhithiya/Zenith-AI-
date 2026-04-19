"""
OAuth callback query validation and stable client-facing error codes.

Google returns opaque `code` and `state` values; we constrain shape and size
to reduce log injection and abuse, and never echo raw exception text to the browser.
"""
from __future__ import annotations

import re
from typing import Optional

OAUTH_CODE_MAX_LEN = 2048
OAUTH_STATE_MAX_LEN = 128
# /auth/login generates UUID4 state values
_STATE_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class OAuthCallbackError(Exception):
    """Invalid or unsupported OAuth callback query parameters."""

    def __init__(self, public_code: str, log_detail: str | None = None) -> None:
        self.public_code = public_code
        self.log_detail = log_detail
        super().__init__(log_detail or public_code)


# Short codes appended as ?auth_error=... (never raw exception strings)
AUTH_ERROR_MESSAGES: dict[str, str] = {
    "missing_params": "Sign-in could not continue because required parameters were missing.",
    "invalid_params": "Sign-in parameters were invalid or too large. Please try again.",
    "invalid_state": "Your sign-in session was invalid or expired. Please try again.",
    "invalid_code": "The authorization response was not accepted. Please try signing in again.",
    "session_expired": "Your sign-in session expired or the server restarted. Please try again.",
    "access_denied": "Sign-in was cancelled or Google did not grant access.",
    "signin_failed": "Google sign-in could not be completed. Please try again.",
    "unexpected": "An unexpected error occurred during sign-in. Please try again.",
}


def validate_oauth_callback_query(
    code: Optional[str], state: Optional[str]
) -> tuple[str, str]:
    """
    Validate OAuth callback query values.

    Returns stripped (code, state). Raises OAuthCallbackError on failure.
    """
    if code is None or state is None:
        raise OAuthCallbackError("missing_params", "code or state missing")

    code_s = code.strip()
    state_s = state.strip()
    if not code_s or not state_s:
        raise OAuthCallbackError("missing_params", "empty code or state after strip")

    if len(code_s) > OAUTH_CODE_MAX_LEN or len(state_s) > OAUTH_STATE_MAX_LEN:
        raise OAuthCallbackError("invalid_params", "code or state exceeds max length")

    if not _STATE_UUID4_RE.match(state_s):
        raise OAuthCallbackError("invalid_state", "state is not a UUID4-shaped value")

    if not code_s.isascii() or any(c in code_s for c in "\n\r\t\x00"):
        raise OAuthCallbackError("invalid_code", "code contains illegal characters")

    if len(code_s) < 10:
        raise OAuthCallbackError("invalid_code", "authorization code too short")

    return code_s, state_s


def classify_oauth_failure(exc: BaseException) -> str:
    """Map internal failures to a stable auth_error code (no sensitive detail)."""
    if isinstance(exc, OAuthCallbackError):
        return exc.public_code

    msg = str(exc).lower()
    if "pkce" in msg or "verifier" in msg or "code verifier" in msg:
        return "session_expired"
    return "signin_failed"
