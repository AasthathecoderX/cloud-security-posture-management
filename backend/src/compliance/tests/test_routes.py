"""
API tests for GET /scans/{scan_id}/compliance.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

BACKEND = Path(__file__).resolve().parents[3]
SRC = BACKEND / "src"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import main
import models as m
import routes
from db import get_session


SEED = [
    ("CIS-AWS-001", "2.1.5", "PR.AC-3"),
    ("CIS-AWS-002", "5.2", "PR.AC-5"),
    ("CIS-AWS-003", "1.16", "PR.AC-4"),
    ("CIS-AWS-004", "2.1.1", "PR.DS-1"),
    ("CIS-AWS-005", "1.16", "PR.AC-4"),
]


class Env:
    def __init__(self, engine, user_id):
        self.engine = engine
        self.user_id = user_id


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for rule_id, cis, nist in SEED:
            session.add(
                m.ComplianceMap(
                    rule_id=rule_id,
                    cis_control_id=cis,
                    nist_id=nist,
                    remediation_steps=f"Remediate {rule_id}",
                )
            )

        user = m.User(
            email="compliance-api@test",
            password_hash="!",
            role=m.UserRole.VIEWER,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        env = Env(engine, user.user_id)

    yield env

    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(env):
    def override_session():
        with Session(env.engine) as session:
            yield session

    def override_user():
        with Session(env.engine) as session:
            return session.exec(
                select(m.User).where(m.User.user_id == env.user_id)
            ).first()

    main.app.dependency_overrides[get_session] = override_session
    main.app.dependency_overrides[routes.get_current_user] = override_user

    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()


def _create_scan(env):
    with Session(env.engine) as session:
        scan = m.Scan(
            user_id=env.user_id,
            filename="compliance-test.json",
            scan_type=m.ScanType.STATIC,
            status=m.ScanStatus.COMPLETED,
        )

        session.add(scan)
        session.commit()
        session.refresh(scan)

        return scan.scan_id


def test_compliance_unknown_scan_returns_404(client):
    response = client.get(
        "/scans/00000000-0000-0000-0000-000000000000/compliance"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Scan not found."


def test_zero_finding_scan_returns_all_pass(client, env):
    scan_id = _create_scan(env)

    response = client.get(
        f"/scans/{scan_id}/compliance"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["scan_id"] == str(scan_id)

    assert body["frameworks"]["CIS"] == {
        "passed": 5,
        "failed": 0,
        "total": 5,
    }

    assert body["frameworks"]["NIST"] == {
        "passed": 5,
        "failed": 0,
        "total": 5,
    }

    assert all(
        control["status"] == "PASS"
        for control in body["controls"]
    )


def test_finding_is_reported_as_failed_control(client, env):
    with Session(env.engine) as session:
        scan = m.Scan(
            user_id=env.user_id,
            filename="bad.json",
            scan_type=m.ScanType.STATIC,
            status=m.ScanStatus.COMPLETED,
        )
        session.add(scan)
        session.commit()
        session.refresh(scan)

        finding = m.Finding(
            scan_id=scan.scan_id,
            resource_id="bucket-001",
            resource_type="s3_bucket",
            severity=m.Severity.HIGH,
            rule_id="CIS-AWS-001",
            message="Public read access",
        )

        session.add(finding)
        session.commit()
        session.refresh(finding)

        scan_id = scan.scan_id
        finding_id = str(finding.finding_id)

    response = client.get(
        f"/scans/{scan_id}/compliance"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["frameworks"]["CIS"]["failed"] == 1
    assert body["frameworks"]["NIST"]["failed"] == 1

    cis_control = next(
        control
        for control in body["controls"]
        if control["framework"] == "CIS"
        and control["rule_id"] == "CIS-AWS-001"
    )

    assert cis_control["status"] == "FAIL"
    assert finding_id in cis_control["finding_ids"]


def test_other_users_scan_is_not_visible(client, env):
    with Session(env.engine) as session:
        other_user = m.User(
            email="other-compliance@test",
            password_hash="!",
            role=m.UserRole.VIEWER,
        )

        session.add(other_user)
        session.commit()
        session.refresh(other_user)

        scan = m.Scan(
            user_id=other_user.user_id,
            filename="private.json",
            scan_type=m.ScanType.STATIC,
            status=m.ScanStatus.COMPLETED,
        )

        session.add(scan)
        session.commit()
        session.refresh(scan)

        scan_id = scan.scan_id

    response = client.get(
        f"/scans/{scan_id}/compliance"
    )

    assert response.status_code == 404