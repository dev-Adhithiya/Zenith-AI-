"""Tests for OAuth callback query validation."""
import pytest

from auth.oauth_callback import (
    OAuthCallbackError,
    validate_oauth_callback_query,
    classify_oauth_failure,
)


def test_validate_accepts_uuid4_state_and_reasonable_code():
    state = "550e8400-e29b-41d4-a716-446655440000"
    code = "4/0AeanS" + "x" * 40  # shape only; not a real Google code
    c, s = validate_oauth_callback_query(code, state)
    assert c == code
    assert s == state


def test_validate_rejects_bad_state():
    with pytest.raises(OAuthCallbackError) as ei:
        validate_oauth_callback_query("4/0AeanSxxxxxxxxxx", "not-a-uuid")
    assert ei.value.public_code == "invalid_state"


def test_validate_rejects_missing():
    with pytest.raises(OAuthCallbackError) as ei:
        validate_oauth_callback_query(None, "550e8400-e29b-41d4-a716-446655440000")
    assert ei.value.public_code == "missing_params"


def test_classify_pkce_value_error():
    class E(ValueError):
        pass

    assert classify_oauth_failure(E("PKCE code verifier not found")) == "session_expired"


def test_classify_generic_value_error():
    assert classify_oauth_failure(ValueError("other")) == "signin_failed"
