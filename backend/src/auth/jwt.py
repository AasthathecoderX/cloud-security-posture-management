"""
JWT utilities for CSPM authentication.

Security properties:
- Explicitly pins HS256.
- Rejects tokens signed with another algorithm.
- Access tokens have a short lifetime.
- Refresh tokens have a longer lifetime.
- Access and refresh tokens carry different token types.
- Refresh tokens carry a unique JTI for rotation tracking.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)


def _get_secret() -> str:
    """
    Load the JWT signing secret.

    A real secret is mandatory. The old Phase 0 placeholder is explicitly
    rejected so authentication cannot accidentally run with the old value.
    """
    secret = os.getenv("JWT_SECRET", "").strip()

    if not secret:
        raise RuntimeError(
            "JWT_SECRET is not configured. Set a strong random JWT_SECRET "
            "in the local .env file."
        )

    placeholder = "local-phase-zero-placeholder-change-before-auth-work"

    if secret == placeholder:
        raise RuntimeError(
            "JWT_SECRET is still using the Phase 0 placeholder. "
            "Generate a real secret before starting authentication."
        )

    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET must contain at least 32 characters."
        )

    return secret


# ---------------------------------------------------------------------------
# Refresh-token rotation registry
# ---------------------------------------------------------------------------

# NOTE:
# The current database schema has no refresh-session/token table.
# Therefore M1 keeps rotation state in memory.
#
# This means:
#   - an issued refresh token can be used once;
#   - after rotation, its JTI is revoked;
#   - the state is lost if the process restarts;
#   - multiple backend workers do not share this state.
#
# A later schema-backed auth-session design can replace this without changing
# the external /auth API contract.

_USED_REFRESH_TOKEN_JTIS: set[str] = set()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _create_token(
    *,
    user_id: UUID,
    email: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> str:
    """
    Create a signed JWT.

    The algorithm is always explicitly passed as HS256.
    """
    now = _utcnow()

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti or str(uuid4()),
    }

    return jwt.encode(
        payload,
        _get_secret(),
        algorithm=JWT_ALGORITHM,
    )


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    user_id: UUID,
    email: str,
    role: str,
) -> str:
    """
    Create a short-lived access token.
    """
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="access",
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(
    *,
    user_id: UUID,
    email: str,
    role: str,
) -> str:
    """
    Create a long-lived refresh token.

    Each refresh token receives a unique JTI.
    """
    return _create_token(
        user_id=user_id,
        email=email,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def decode_token(
    token: str,
    expected_type: str,
) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Security requirements:
    - signature must be valid;
    - algorithm must be HS256;
    - token must not be expired;
    - token type must match the expected type;
    - required subject/JTI claims must exist.

    Raises:
        jwt.InvalidTokenError: When validation fails.
    """
    if not token:
        raise jwt.InvalidTokenError("Missing token.")

    # Inspect the header only to explicitly reject unexpected algorithms.
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise jwt.InvalidTokenError(
            "Invalid token header."
        ) from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise jwt.InvalidAlgorithmError(
            "Invalid JWT algorithm."
        )

    # Explicitly provide the permitted algorithm instead of trusting
    # whatever algorithm is present in the token header.
    payload = jwt.decode(
        token,
        _get_secret(),
        algorithms=[JWT_ALGORITHM],
        options={
            "require": [
                "exp",
                "iat",
                "sub",
                "type",
                "jti",
            ],
        },
    )

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            "Invalid token type."
        )

    if not payload.get("sub"):
        raise jwt.InvalidTokenError(
            "Missing subject."
        )

    if not payload.get("jti"):
        raise jwt.InvalidTokenError(
            "Missing token identifier."
        )

    return payload


# ---------------------------------------------------------------------------
# Refresh-token rotation
# ---------------------------------------------------------------------------

def rotate_refresh_token(token: str) -> str:
    """
    Validate a refresh token and rotate it.

    Returns:
        A newly generated refresh-token string.

    The old token's JTI is marked as used so it cannot be refreshed twice
    during the lifetime of this backend process.
    """
    payload = decode_token(
        token,
        expected_type="refresh",
    )

    old_jti = str(payload["jti"])

    if old_jti in _USED_REFRESH_TOKEN_JTIS:
        raise jwt.InvalidTokenError(
            "Refresh token has already been used."
        )

    # Mark the old refresh token as used before issuing the replacement.
    _USED_REFRESH_TOKEN_JTIS.add(old_jti)

    try:
        user_id = UUID(str(payload["sub"]))
    except (ValueError, TypeError) as exc:
        raise jwt.InvalidTokenError(
            "Invalid user identifier."
        ) from exc

    email = str(payload.get("email", ""))
    role = str(payload.get("role", ""))

    new_refresh_token = create_refresh_token(
        user_id=user_id,
        email=email,
        role=role,
    )

    # IMPORTANT:
    # The public contract of this function is to return only the new JWT.
    return new_refresh_token


# ---------------------------------------------------------------------------
# Refresh-token revocation
# ---------------------------------------------------------------------------

def revoke_refresh_token(token: str) -> None:
    """
    Mark a refresh token as used/revoked.

    Invalid tokens are intentionally ignored here because logout should not
    leak information about whether a supplied token was valid.
    """
    try:
        payload = decode_token(
            token,
            expected_type="refresh",
        )

        jti = str(payload["jti"])
        _USED_REFRESH_TOKEN_JTIS.add(jti)

    except jwt.InvalidTokenError:
        return


# ---------------------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """
    Generate a cryptographically random CSRF token.
    """
    return secrets.token_urlsafe(32)


def hash_csrf_token(token: str) -> str:
    """
    Hash a CSRF token before comparing/storing it internally.

    This is not password hashing; SHA-256 is appropriate for a random,
    high-entropy CSRF nonce.
    """
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def verify_csrf_token(
    raw_token: str,
    expected_token: str,
) -> bool:
    """
    Verify a supplied CSRF token against an expected token or hash
    using constant-time comparison.
    """
    if not raw_token or not expected_token:
        return False

    # If the expected value is a SHA-256 hex digest, hash the supplied
    # token before performing the constant-time comparison.
    if (
        len(expected_token) == 64
        and all(
            c in "0123456789abcdefABCDEF"
            for c in expected_token
        )
    ):
        token_hash = hash_csrf_token(raw_token)

        return hmac.compare_digest(
            token_hash.lower(),
            expected_token.lower(),
        )

    # Otherwise compare the raw token directly.
    return hmac.compare_digest(
        raw_token,
        expected_token,
    )