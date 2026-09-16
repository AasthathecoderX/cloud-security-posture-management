"""
Phase 2 API tests (Member 4).

Exercises the full FastAPI stack end to end against a throwaway in-memory SQLite
database, with the ``get_session`` and ``get_current_user`` dependencies
overridden so tests never touch a real database and can simulate multiple users.

Covers:
- Happy path: upload a bad fixture -> it is stored -> read it back via GET.
- Findings are actually persisted in the database.
- Good fixtures produce zero findings.
- Validation failures return a clean 400 (bad extension, oversized, deep nesting,
  YAML alias bomb) -- never a 500.
- IDOR: user B cannot read user A's scan (404), and listings are user-scoped.
"""

import sys
from pathlib import Path

# Make ``backend/`` importable so ``import main`` works (conftest already adds
# ``backend/src`` for the src modules).
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import main
import models as m
import routes
from db import get_session

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# rule_id, cis_control_id, nist_id  (remediation text is not asserted here)
_SEED = [
    ("CIS-AWS-001", "2.1.5", "PR.AC-3"),
    ("CIS-AWS-002", "5.2", "PR.AC-5"),
    ("CIS-AWS-003", "1.16", "PR.AC-4"),
    ("CIS-AWS-004", "2.1.1", "PR.DS-1"),
    ("CIS-AWS-005", "1.16", "PR.AC-4"),
]


class _Env:
    def __init__(self, engine, user_a, user_b):
        self.engine = engine
        self.user_a = user_a
        self.user_b = user_b
        self.current = user_a  # which user the overridden dependency returns


@pytest.fixture()
def env():
    """A fresh in-memory schema, seeded compliance_map, and two users."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _):  # enforce FKs so findings.rule_id is checked
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for rule_id, cis, nist in _SEED:
            session.add(
                m.ComplianceMap(
                    rule_id=rule_id,
                    cis_control_id=cis,
                    nist_id=nist,
                    remediation_steps="see rule",
                )
            )
        user_a = m.User(email="a@test", password_hash="!", role=m.UserRole.ADMIN)
        user_b = m.User(email="b@test", password_hash="!", role=m.UserRole.VIEWER)
        session.add(user_a)
        session.add(user_b)
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)
        e = _Env(engine, user_a.user_id, user_b.user_id)

    yield e

    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(env):
    """TestClient wired to the throwaway DB and a switchable current user."""

    def override_session():
        with Session(env.engine) as session:
            yield session

    def override_user():
        with Session(env.engine) as session:
            return session.exec(
                select(m.User).where(m.User.user_id == env.current)
            ).first()

    main.app.dependency_overrides[get_session] = override_session
    main.app.dependency_overrides[routes.get_current_user] = override_user
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()


def _upload(client, name, content, content_type="application/json"):
    return client.post(
        "/scans/upload", files={"file": (name, content, content_type)}
    )


# ---------------- Happy path ---------------- #

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_upload_bad_fixture_stored_and_readback(client):
    content = (FIXTURES / "bad" / "s3_public_read.json").read_bytes()
    r = _upload(client, "s3_public_read.json", content)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["findings_count"] == 1
    assert body["status"] == "COMPLETED"
    scan_id = body["scan_id"]

    # list
    r = client.get("/scans")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["scan_id"] == scan_id
    assert r.json()[0]["filename"] == "s3_public_read.json"

    # detail
    r = client.get(f"/scans/{scan_id}")
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["rule_id"] == "CIS-AWS-001"
    assert detail["findings"][0]["severity"] == "High"
    # Wave A / Member 4: risk_score and is_anomaly are populated at scan time.
    assert isinstance(detail["findings"][0]["risk_score"], int)
    assert isinstance(detail["findings"][0]["is_anomaly"], bool)

    # findings endpoint
    r = client.get(f"/scans/{scan_id}/findings")
    assert r.status_code == 200
    assert [f["rule_id"] for f in r.json()] == ["CIS-AWS-001"]


def test_findings_persisted_in_db(client, env):
    content = (FIXTURES / "bad" / "security_group_open.yaml").read_bytes()
    r = _upload(client, "security_group_open.yaml", content, "application/x-yaml")
    assert r.status_code == 200

    with Session(env.engine) as session:
        scans = session.exec(select(m.Scan)).all()
        findings = session.exec(select(m.Finding)).all()
    assert len(scans) == 1
    assert len(findings) == 1
    assert findings[0].rule_id == "CIS-AWS-002"
    assert findings[0].scan_id == scans[0].scan_id


def test_upload_good_fixture_zero_findings(client):
    content = (FIXTURES / "good" / "s3_bucket.json").read_bytes()
    r = _upload(client, "s3_bucket.json", content)
    assert r.status_code == 200
    assert r.json()["findings_count"] == 0


# ---------------- Validation failures (clean 400) ---------------- #

def test_upload_rejects_bad_extension(client):
    r = _upload(client, "evil.txt", b"whatever", "text/plain")
    assert r.status_code == 400


def test_upload_rejects_oversized(client):
    payload = b'{"resource_id":"x","resource_type":"s3_bucket","pad":"' + b"A" * (
        2 * 1024 * 1024 + 32
    ) + b'"}'
    r = _upload(client, "big.json", payload)
    assert r.status_code == 400


def test_upload_rejects_deep_nesting(client):
    payload = ("[" * 60) + "0" + ("]" * 60)
    r = _upload(client, "deep.json", payload.encode())
    assert r.status_code == 400


def test_upload_rejects_recursion_bomb(client):
    # Deeply-nested JSON raises RecursionError in the loader; it must still be a
    # clean 400, not an unhandled 500.
    payload = ("[" * 100000) + "0" + ("]" * 100000)
    r = _upload(client, "bomb.json", payload.encode())
    assert r.status_code == 400


def test_oversized_request_rejected_at_edge(client):
    # Body larger than the middleware cap is rejected with 413 before buffering.
    payload = b'{"pad":"' + b"A" * (2 * 1024 * 1024 + 128 * 1024) + b'"}'
    r = _upload(client, "huge.json", payload)
    assert r.status_code == 413


def test_upload_rejects_yaml_alias_bomb(client):
    payload = b"a: &anchor [1, 2, 3]\nb: *anchor\n"
    r = _upload(client, "bomb.yaml", payload, "application/x-yaml")
    assert r.status_code == 400


def test_upload_rejects_malformed_json(client):
    r = _upload(client, "broken.json", b"{not valid json")
    assert r.status_code == 400


# ---------------- Access control (IDOR / scoping) ---------------- #

def test_idor_other_user_cannot_read_scan(client, env):
    content = (FIXTURES / "bad" / "s3_public_read.json").read_bytes()
    scan_id = _upload(client, "s3_public_read.json", content).json()["scan_id"]

    # Switch the current user to B and try to read A's scan.
    env.current = env.user_b
    assert client.get(f"/scans/{scan_id}").status_code == 404
    assert client.get(f"/scans/{scan_id}/findings").status_code == 404


def test_scans_are_user_scoped(client, env):
    content = (FIXTURES / "bad" / "s3_public_read.json").read_bytes()
    _upload(client, "s3_public_read.json", content)

    # A has one scan.
    assert len(client.get("/scans").json()) == 1

    # B has none.
    env.current = env.user_b
    assert client.get("/scans").json() == []


def test_unknown_scan_id_returns_404(client):
    import uuid

    r = client.get(f"/scans/{uuid.uuid4()}")
    assert r.status_code == 404
