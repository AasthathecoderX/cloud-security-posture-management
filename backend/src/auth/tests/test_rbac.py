"""Focused tests for the RBAC dependency contract."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from auth.dependencies import get_current_user
from auth.rbac import require_role
from db import get_session
from models import AuditLog, User, UserRole


def _client_for_role(role: UserRole):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(email=f"{role.value.lower()}@example.test", password_hash="test", role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        app = FastAPI()

        def fake_user():
            return user

        def fake_session():
            return session

        app.dependency_overrides[get_current_user] = fake_user
        app.dependency_overrides[get_session] = fake_session

        @app.post("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
        def admin_only():
            return {"ok": True}

        @app.get("/read", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.VIEWER))])
        def read_only():
            return {"ok": True}

        return TestClient(app), engine


def test_admin_allowed_for_admin_endpoint():
    client, engine = _client_for_role(UserRole.ADMIN)
    try:
        assert client.post("/admin").status_code == 200
    finally:
        engine.dispose()


def test_viewer_denied_for_admin_endpoint_and_audited():
    client, engine = _client_for_role(UserRole.VIEWER)
    try:
        assert client.post("/admin").status_code == 403
        with Session(engine) as session:
            events = session.query(AuditLog).filter(
                AuditLog.action == "role_check_denied"
            ).all()
            assert len(events) == 1
            assert events[0].user_id is not None
    finally:
        engine.dispose()


def test_empty_allowed_roles_fails_closed():
    client, engine = _client_for_role(UserRole.ADMIN)
    try:
        app = client.app
        @app.get("/no-roles", dependencies=[Depends(require_role())])
        def no_roles():
            return {"ok": True}
        assert client.get("/no-roles").status_code == 403
    finally:
        engine.dispose()


def test_viewer_can_read():
    client, engine = _client_for_role(UserRole.VIEWER)
    try:
        assert client.get("/read").status_code == 200
    finally:
        engine.dispose()
