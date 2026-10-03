"""
M1 JWT unit tests.

Tests:
- access token creation
- refresh token creation
- token decoding
- token type validation
- expiration validation
- invalid/tampered tokens
- refresh-token rotation
- refresh-token reuse detection
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest

os.environ.setdefault(
    "JWT_SECRET",
    "m1-test-secret-please-change-this-to-a-long-random-value-123456789",
)

from auth.jwt import (
    JWT_ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_refresh_token,
    rotate_refresh_token,
)


TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_EMAIL = "test@example.com"
TEST_ROLE = "viewer"


def test_create_and_decode_access_token():
    token = create_access_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    assert isinstance(token, str)
    assert token

    payload = decode_token(
        token,
        expected_type="access",
    )

    assert payload["sub"] == TEST_USER_ID
    assert payload["email"] == TEST_EMAIL
    assert payload["role"] == TEST_ROLE
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload


def test_create_and_decode_refresh_token():
    token = create_refresh_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    assert isinstance(token, str)
    assert token

    payload = decode_token(
        token,
        expected_type="refresh",
    )

    assert payload["sub"] == TEST_USER_ID
    assert payload["email"] == TEST_EMAIL
    assert payload["role"] == TEST_ROLE
    assert payload["type"] == "refresh"
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload


def test_access_token_cannot_be_used_as_refresh_token():
    token = create_access_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(
            token,
            expected_type="refresh",
        )


def test_refresh_token_cannot_be_used_as_access_token():
    token = create_refresh_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(
            token,
            expected_type="access",
        )


def test_tampered_token_is_rejected():
    token = create_access_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    parts = token.split(".")

    assert len(parts) == 3

    tampered_payload = parts[1][::-1]

    tampered_token = (
        f"{parts[0]}.{tampered_payload}.{parts[2]}"
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(
            tampered_token,
            expected_type="access",
        )


def test_malformed_token_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(
            "this-is-not-a-valid-jwt",
            expected_type="access",
        )


def test_wrong_algorithm_is_rejected():
    payload = {
        "sub": TEST_USER_ID,
        "email": TEST_EMAIL,
        "role": TEST_ROLE,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "jti": "test-jti",
    }

    token = jwt.encode(
        payload,
        os.environ["JWT_SECRET"],
        algorithm="HS384",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(
            token,
            expected_type="access",
        )


def test_expired_token_is_rejected():
    payload = {
        "sub": TEST_USER_ID,
        "email": TEST_EMAIL,
        "role": TEST_ROLE,
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=30),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=15),
        "jti": "expired-jti",
    }

    token = jwt.encode(
        payload,
        os.environ["JWT_SECRET"],
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(
            token,
            expected_type="access",
        )


def test_refresh_token_rotation_returns_new_token():
    original_token = create_refresh_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    new_token = rotate_refresh_token(original_token)

    assert isinstance(new_token, str)
    assert new_token
    assert new_token != original_token

    payload = decode_token(
        new_token,
        expected_type="refresh",
    )

    assert payload["sub"] == TEST_USER_ID
    assert payload["type"] == "refresh"


def test_rotated_refresh_token_cannot_be_reused():
    original_token = create_refresh_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    rotate_refresh_token(original_token)

    with pytest.raises(jwt.InvalidTokenError):
        rotate_refresh_token(original_token)


def test_revoke_refresh_token_prevents_reuse():
    token = create_refresh_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role=TEST_ROLE,
    )

    revoke_refresh_token(token)

    with pytest.raises(jwt.InvalidTokenError):
        rotate_refresh_token(token)