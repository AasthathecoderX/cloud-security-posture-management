"""
Integration tests for M1 authentication routes.

These tests use a temporary SQLite database and exercise the real authentication
dependency instead of replacing get_current_user with a fake user.
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool


# Ensure backend/src imports work when this file is executed directly.
SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import db
import main
from auth.jwt import generate_csrf_token
from db import get_session


@pytest.fixture()
def test_engine():
    """
    Create a fresh in-memory SQLite database for each test.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(engine)

    yield engine

    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(test_engine):
    """
    Build a TestClient using the temporary database.
    """

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    main.app.dependency_overrides[get_session] = override_get_session

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


def _bootstrap_csrf(client: TestClient) -> str:
    """
    GET /auth/me creates the initial CSRF cookie.

    The endpoint is expected to return 401 because no user is logged in.
    """
    response = client.get("/auth/me")

    assert response.status_code == 401

    csrf_token = client.cookies.get("csrf_token")

    assert csrf_token is not None

    return csrf_token


def test_signup_creates_user_and_sets_cookies(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    response = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["email"] == "alice@example.com"
    assert body["role"] == "VIEWER"
    assert "user_id" in body

    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")


def test_signup_stores_hashed_password(client: TestClient, test_engine):
    csrf_token = _bootstrap_csrf(client)

    response = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 201

    from models import User

    with Session(test_engine) as session:
        user = session.query(User).filter(
            User.email == "alice@example.com"
        ).first()

        assert user is not None
        assert user.password_hash != "CorrectPassword123!"
        assert user.password_hash.startswith("$argon2")


def test_duplicate_signup_is_rejected(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    payload = {
        "email": "alice@example.com",
        "password": "CorrectPassword123!",
    }

    first = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )

    assert first.status_code == 201

    # Refresh the CSRF value from the cookie.
    csrf_token = client.cookies.get("csrf_token")

    second = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json=payload,
    )

    assert second.status_code == 409


def test_login_with_correct_password_succeeds(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    # Simulate a new client/session by clearing authentication cookies.
    client.cookies.delete("access_token")
    client.cookies.delete("refresh_token")

    csrf_token = client.cookies.get("csrf_token")

    response = client.post(
        "/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"

    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")


def test_wrong_password_returns_generic_error(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    client.cookies.delete("access_token")
    client.cookies.delete("refresh_token")

    csrf_token = client.cookies.get("csrf_token")

    response = client.post(
        "/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_nonexistent_email_returns_same_generic_error(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    response = client.post(
        "/auth/login",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "doesnotexist@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_returns_authenticated_user(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    response = client.get("/auth/me")

    assert response.status_code == 200

    body = response.json()

    assert body["email"] == "alice@example.com"
    assert body["role"] == "VIEWER"
    assert "user_id" in body


def test_me_requires_authentication(client: TestClient):
    _bootstrap_csrf(client)

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_refresh_rotates_refresh_cookie(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    old_refresh = client.cookies.get("refresh_token")

    csrf_token = client.cookies.get("csrf_token")

    response = client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200

    new_refresh = client.cookies.get("refresh_token")

    assert old_refresh is not None
    assert new_refresh is not None
    assert new_refresh != old_refresh


def test_old_refresh_token_cannot_be_used_twice(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    old_refresh = client.cookies.get("refresh_token")

    # First refresh.
    csrf_token = client.cookies.get("csrf_token")

    first_refresh = client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert first_refresh.status_code == 200

    # Replace the current refresh cookie with the old token.
    client.cookies.set(
        "refresh_token",
        old_refresh,
        path="/auth",
    )

    csrf_token = client.cookies.get("csrf_token")

    second_refresh = client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert second_refresh.status_code == 401


def test_logout_clears_authentication(client: TestClient):
    csrf_token = _bootstrap_csrf(client)

    signup = client.post(
        "/auth/signup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert signup.status_code == 201

    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")

    csrf_token = client.cookies.get("csrf_token")

    response = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 204

    me = client.get("/auth/me")

    assert me.status_code == 401


def test_missing_csrf_token_is_rejected(client: TestClient):
    _bootstrap_csrf(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "alice@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 403


def test_missing_access_cookie_is_rejected(client: TestClient):
    _bootstrap_csrf(client)

    response = client.get("/auth/me")

    assert response.status_code == 401