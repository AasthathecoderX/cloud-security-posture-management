"""
Tests for the Phase 7 compliance aggregation engine.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import yaml
from sqlmodel import Session, SQLModel, create_engine

# Make backend/src importable when this test is run directly.
SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import models as m
from compliance.engine import build_compliance


REPO_ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = REPO_ROOT / "rules"

EXPECTED_SEED_RULES = {
    "CIS-AWS-001",
    "CIS-AWS-002",
    "CIS-AWS-003",
    "CIS-AWS-004",
    "CIS-AWS-005",
}

def _seed_session():
    engine = create_engine("sqlite://")

    SQLModel.metadata.create_all(engine)

    session = Session(engine)

    for idx, rule_id in enumerate(sorted(EXPECTED_SEED_RULES)):
        session.add(
            m.ComplianceMap(
                rule_id=rule_id,
                cis_control_id=f"cis-{idx}",
                nist_id=f"nist-{idx}",
                remediation_steps="test remediation",
            )
        )

    session.commit()

    return engine, session


def test_all_rule_yaml_ids_have_compliance_seed_rows():
    """
    Every real rule YAML file must have a corresponding compliance-map seed.

    spec.yaml is documentation and is intentionally excluded.
    """
    yaml_rule_ids = set()

    for path in sorted(RULES_DIR.glob("*.yaml")):
        if path.name == "spec.yaml":
            continue

        with path.open("r", encoding="utf-8") as file:
            rule = yaml.safe_load(file)

        assert isinstance(rule, dict), f"Invalid rule file: {path}"
        assert rule.get("rule_id"), f"Missing rule_id in {path}"

        yaml_rule_ids.add(rule["rule_id"])

    assert yaml_rule_ids == EXPECTED_SEED_RULES


def test_zero_findings_marks_all_controls_pass():
    engine, session = _seed_session()

    try:
        result = build_compliance(
            session=session,
            findings=[],
        )

        assert result["frameworks"]["CIS"]["failed"] == 0
        assert result["frameworks"]["CIS"]["passed"] == 5
        assert result["frameworks"]["CIS"]["total"] == 5

        assert result["frameworks"]["NIST"]["failed"] == 0
        assert result["frameworks"]["NIST"]["passed"] == 5
        assert result["frameworks"]["NIST"]["total"] == 5

        assert all(
            control["status"] == "PASS"
            for control in result["controls"]
        )
    finally:
        session.close()
        SQLModel.metadata.drop_all(engine)


def test_finding_marks_matching_rule_failed():
    engine, session = _seed_session()

    try:
        user = m.User(
            email="compliance@test",
            password_hash="!",
            role=m.UserRole.VIEWER,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        scan = m.Scan(
            user_id=user.user_id,
            filename="test.json",
            scan_type=m.ScanType.STATIC,
            status=m.ScanStatus.COMPLETED,
        )
        session.add(scan)
        session.commit()
        session.refresh(scan)

        finding = m.Finding(
            scan_id=scan.scan_id,
            resource_id="bucket-1",
            resource_type="s3_bucket",
            severity=m.Severity.HIGH,
            rule_id="CIS-AWS-001",
            message="Public read access",
        )
        session.add(finding)
        session.commit()
        session.refresh(finding)

        result = build_compliance(
            session=session,
            findings=[finding],
        )

        cis_failed = [
            control
            for control in result["controls"]
            if control["framework"] == "CIS"
            and control["rule_id"] == "CIS-AWS-001"
        ]

        nist_failed = [
            control
            for control in result["controls"]
            if control["framework"] == "NIST"
            and control["rule_id"] == "CIS-AWS-001"
        ]

        assert cis_failed[0]["status"] == "FAIL"
        assert nist_failed[0]["status"] == "FAIL"

        assert str(finding.finding_id) in cis_failed[0]["finding_ids"]
        assert str(finding.finding_id) in nist_failed[0]["finding_ids"]
    finally:
        session.close()
        SQLModel.metadata.drop_all(engine)


def test_unmapped_finding_does_not_crash():
    engine, session = _seed_session()

    try:
        user = m.User(
            email="unmapped@test",
            password_hash="!",
            role=m.UserRole.VIEWER,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        scan = m.Scan(
            user_id=user.user_id,
            filename="test.json",
            scan_type=m.ScanType.STATIC,
            status=m.ScanStatus.COMPLETED,
        )
        session.add(scan)
        session.commit()
        session.refresh(scan)

        # Bypass the FK intentionally by constructing a lightweight fake
        # finding whose compliance relationship is None.
        class UnmappedFinding:
            finding_id = uuid4()
            rule_id = "UNKNOWN-RULE"
            compliance = None

        result = build_compliance(
            session=session,
            findings=[UnmappedFinding()],
        )

        assert result["frameworks"]["CIS"]["failed"] == 0
        assert result["frameworks"]["NIST"]["failed"] == 0
    finally:
        session.close()
        SQLModel.metadata.drop_all(engine)