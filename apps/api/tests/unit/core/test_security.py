"""Password hashing, JWT dashboard sessions (audience and expiry enforcement), and
organization API key generation/parsing/hashing, with no database dependency."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from agenteval.core.security import (
    API_KEY_PREFIX,
    SESSION_AUDIENCE,
    constant_time_equals,
    decode_session,
    generate_api_key,
    hash_key_secret,
    hash_password,
    issue_session,
    parse_api_key,
    password_problems,
    verify_password,
)


def test_hash_password_produces_a_verifiable_hash() -> None:
    hashed = hash_password("Correct-Horse-9")
    assert verify_password("Correct-Horse-9", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_is_false_for_a_none_hash() -> None:
    """An unknown email has no stored hash at all; this must fail closed, never raise."""
    assert verify_password("anything", None) is False


@pytest.mark.parametrize(
    ("password", "expected_substring"),
    [
        ("short1A", "at least 10 characters"),
        ("alllowercase1", "upper and lower"),
        ("ALLUPPERCASE1", "upper and lower"),
        ("NoDigitsHere", "a digit"),
    ],
)
def test_password_problems_flags_each_real_weakness(password: str, expected_substring: str) -> None:
    problems = password_problems(password)
    assert any(expected_substring in p for p in problems)


def test_password_problems_is_empty_for_a_strong_password() -> None:
    assert password_problems("Correct-Horse-9") == []


def test_issue_and_decode_session_round_trips() -> None:
    user_id = uuid.uuid4()
    token = issue_session(
        user_id, session_version=3, secret="a-test-secret-that-is-long-enough-32", ttl_hours=12
    )
    claims = decode_session(token, "a-test-secret-that-is-long-enough-32")
    assert claims is not None
    assert claims.user_id == user_id
    assert claims.session_version == 3


def test_decode_session_rejects_the_wrong_secret() -> None:
    token = issue_session(
        uuid.uuid4(), session_version=0, secret="a-test-secret-that-is-long-enough-aa", ttl_hours=12
    )
    assert decode_session(token, "a-test-secret-that-is-long-enough-bb") is None


def test_decode_session_rejects_an_expired_token() -> None:
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sv": 0,
        "aud": SESSION_AUDIENCE,
        "iat": now - timedelta(hours=13),
        "exp": now - timedelta(hours=1),
        "jti": "test",
    }
    expired = jwt.encode(payload, "a-test-secret-that-is-long-enough-32", algorithm="HS256")
    assert decode_session(expired, "a-test-secret-that-is-long-enough-32") is None


def test_decode_session_rejects_the_wrong_audience() -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "sv": 0,
        "aud": "some-other-audience",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": "test",
    }
    wrong_audience = jwt.encode(payload, "a-test-secret-that-is-long-enough-32", algorithm="HS256")
    assert decode_session(wrong_audience, "a-test-secret-that-is-long-enough-32") is None


def test_decode_session_rejects_garbage_input() -> None:
    assert decode_session("not-a-real-token", "a-test-secret-that-is-long-enough-32") is None


def test_generate_api_key_round_trips_through_parse_and_hash() -> None:
    generated = generate_api_key(pepper="a-test-pepper")
    assert generated.plaintext.startswith(f"{API_KEY_PREFIX}_")
    parsed = parse_api_key(generated.plaintext)
    assert parsed is not None
    prefix, secret = parsed
    assert prefix == generated.prefix
    assert hash_key_secret(secret, "a-test-pepper") == generated.secret_hash


def test_parse_api_key_rejects_malformed_input() -> None:
    assert parse_api_key("not-a-key-at-all") is None
    assert parse_api_key(f"{API_KEY_PREFIX}_tooshortprefix_secret") is None
    assert parse_api_key("wrongprefix_abcdefabcdef_secret") is None


def test_hash_key_secret_is_deterministic_for_the_same_pepper() -> None:
    assert hash_key_secret("my-secret", "pepper-a") == hash_key_secret("my-secret", "pepper-a")


def test_hash_key_secret_differs_across_peppers() -> None:
    assert hash_key_secret("my-secret", "pepper-a") != hash_key_secret("my-secret", "pepper-b")


def test_constant_time_equals() -> None:
    assert constant_time_equals("abc", "abc") is True
    assert constant_time_equals("abc", "abd") is False
