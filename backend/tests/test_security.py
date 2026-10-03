"""
Wave C, Member 4 -- attacker-perspective security tests.

These test the app the way an attacker would probe it, not the happy path
M1/M2/M3's own suites already cover: forged tokens, missing auth, rate-limit
abuse, and a misconfigured CORS origin. See docs/asvs-l1-checklist.md for how
each test here maps to an ASVS L1 control.

Three tests are marked `xfail(strict=True)`, tied to specific line items in
`guides/wave C/Wave_C_Detailed_Execution_Plan.md`'s "Status check" table.
They encode the behavior Wave C is *supposed* to have once M1/M3 finish, and
are written now so they fail loudly (not silently skip) today, and so
`strict=True` turns into a hard failure -- "remove this xfail" -- the day
someone fixes the underlying gap and forgets to update this file.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault(
    "JWT_SECRET",
    "m4-security-test-secret-please-change-this-to-a-long-random-value-000",
)

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import main
from auth.jwt import create_access_token, decode_token
from db import get_session
from main import validate_cors_origins


# --------------------------------------------------------------------------
# JWT forgery
# --------------------------------------------------------------------------


def test_jwt_rejects_none_algorithm():
    """A classic JWT bypass: re-sign the token claiming alg=none."""
    real_token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        email="attacker@example.com",
        role="ADMIN",
    )
    header, payload, _signature = real_token.split(".")

    forged = jwt.api_jws.encode(
        jwt.utils.base64url_decode(payload.encode() + b"=="),
        key=None,
        algorithm="none",
        headers={"typ": "JWT"},
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(forged, expected_type="access")


def test_jwt_rejects_tampered_signature():
    """Flipping one character of the signature must invalidate the token."""
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        email="user@example.com",
        role="VIEWER",
    )
    header, payload, signature = token.split(".")
    tampered_char = "A" if signature[-1] != "A" else "B"
    tampered = f"{header}.{payload}.{tampered_char}{signature[1:]}"

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered, expected_type="access")


# --------------------------------------------------------------------------
# CORS misconfiguration (pure function -- see main.py for why)
# --------------------------------------------------------------------------


def test_cors_rejects_wildcard_origin():
    with pytest.raises(RuntimeError, match="must not contain"):
        validate_cors_origins(["*"])


def test_cors_accepts_a_real_origin_list():
    validate_cors_origins(["http://localhost:5173"])  # must not raise


# --------------------------------------------------------------------------
# Shared client fixture (fresh DB per test)
# --------------------------------------------------------------------------


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = override_get_session
    with TestClient(main.app) as test_client:
        yield test_client, engine
    main.app.dependency_overrides.clear()


def _csrf(test_client: TestClient) -> str:
    test_client.get("/auth/me")
    token = test_client.cookies.get("csrf_token")
    assert token is not None
    return token


# --------------------------------------------------------------------------
# Authentication is actually required
# --------------------------------------------------------------------------


def test_me_without_a_cookie_is_401(client):
    test_client, _engine = client
    response = test_client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Wave C Status check #1: routes.py's get_current_user is still "
        "shadowed by the old dev-user placeholder, so a feature endpoint "
        "accepts requests with no session at all. This should be 401. "
        "Remove this xfail once the shadowing bug is fixed."
    ),
)
def test_scans_without_a_cookie_is_401(client):
    test_client, _engine = client
    response = test_client.get("/scans")
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------


def test_login_rate_limit_returns_429_after_five_attempts(client):
    test_client, _engine = client
    csrf_token = _csrf(test_client)

    for _ in range(5):
        response = test_client.post(
            "/auth/login",
            headers={"X-CSRF-Token": csrf_token},
            json={"email": "nobody@example.com", "password": "wrong-password-123"},
        )
        assert response.status_code == 401  # wrong credentials, not yet rate-limited

    sixth = test_client.post(
        "/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "nobody@example.com", "password": "wrong-password-123"},
    )
    assert sixth.status_code == 429


def test_signup_rate_limit_returns_429_after_five_attempts(client):
    test_client, _engine = client
    csrf_token = _csrf(test_client)

    for i in range(5):
        test_client.post(
            "/auth/signup",
            headers={"X-CSRF-Token": csrf_token},
            json={"email": f"user{i}@example.com", "password": "CorrectPassword123!"},
        )

    sixth = test_client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "user6@example.com", "password": "CorrectPassword123!"},
    )
    assert sixth.status_code == 429


# --------------------------------------------------------------------------
# RBAC and IDOR under *real* (signed-up) identities, not dependency_overrides
# --------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Wave C Status check #2: every signup is hardcoded to VIEWER with "
        "no bootstrap path to ADMIN, and require_role() doesn't exist yet "
        "(Member 3's work). A Viewer should get 403 on upload; today there "
        "is no role check at all. Remove this xfail once both land."
    ),
)
def test_viewer_cannot_upload_a_scan(client):
    test_client, _engine = client
    csrf_token = _csrf(test_client)

    test_client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "viewer@example.com", "password": "CorrectPassword123!"},
    )

    response = test_client.post(
        "/scans/upload",
        headers={"X-CSRF-Token": csrf_token},
        files={
            "file": (
                "x.json",
                b'{"resource_id":"a","resource_type":"s3_bucket"}',
                "application/json",
            )
        },
    )
    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Wave C Status check #1: because get_current_user is shadowed, "
        "every request -- regardless of whose session cookie it carries -- "
        "resolves to the same auto-created dev@local placeholder. Two real, "
        "separately signed-up users therefore can't be distinguished, so "
        "this can't yet prove scan ownership is scoped per real user. "
        "Remove this xfail once the shadowing bug is fixed."
    ),
)
def test_two_real_users_do_not_share_scan_ownership(client):
    test_client, engine = client
    csrf_token = _csrf(test_client)

    alice = test_client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={"email": "alice@example.com", "password": "CorrectPassword123!"},
    ).json()

    test_client.post(
        "/scans/upload",
        headers={"X-CSRF-Token": csrf_token},
        files={
            "file": (
                "x.json",
                b'{"resource_id":"a","resource_type":"s3_bucket"}',
                "application/json",
            )
        },
    )

    import models as m
    from sqlmodel import select

    with Session(engine) as session:
        scans = session.exec(select(m.Scan)).all()
        assert len(scans) == 1
        assert str(scans[0].user_id) == alice["user_id"]
