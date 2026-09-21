"""
Phase 7 Compliance Engine.

Aggregates scan findings against the existing ComplianceMap relationship.

Important:
- Finding.rule_id -> ComplianceMap.rule_id is already the mapping.
- No second mapping system is created here.
- PASS means that no finding was produced for that rule in this scan.
- PASS does NOT mean that every resource was individually verified.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import yaml
from sqlmodel import Session, select

from models import ComplianceMap, Finding

logger = logging.getLogger(__name__)


_DEFAULT_RULES_DIR = Path(__file__).resolve().parents[3] / "rules"
RULES_DIR = Path(
    os.getenv("RULES_DIR", str(_DEFAULT_RULES_DIR))
)


def _load_rule_titles() -> Dict[str, str]:
    """
    Load rule_id -> rule name from the existing declarative rule files.

    ComplianceMap intentionally stores control IDs and remediation text, but
    not the human-readable rule name. The existing YAML rules are therefore
    used only for presentation metadata.
    """
    titles: Dict[str, str] = {}

    if not RULES_DIR.exists():
        logger.warning("Rules directory does not exist: %s", RULES_DIR)
        return titles

    rule_files = sorted(
        set(RULES_DIR.glob("*.yaml"))
        | set(RULES_DIR.glob("*.yml"))
    )

    for rule_file in rule_files:
        if rule_file.name == "spec.yaml":
            continue

        try:
            with rule_file.open("r", encoding="utf-8") as file:
                rule = yaml.safe_load(file)

            if not isinstance(rule, dict):
                continue

            rule_id = rule.get("rule_id")
            name = rule.get("name")

            if rule_id and name:
                titles[str(rule_id)] = str(name)

        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "Could not read rule metadata from %s: %s",
                rule_file,
                exc,
            )

    return titles


def _finding_ids_by_rule(
    findings: Iterable[Finding],
) -> Dict[str, List[str]]:
    """
    Group finding IDs by rule_id.

    Findings without a ComplianceMap relationship are ignored by the
    aggregation but logged by the caller.
    """
    result: Dict[str, List[str]] = {}

    for finding in findings:
        if finding.compliance is None:
            logger.warning(
                "Finding %s has no compliance mapping; ignoring it.",
                finding.finding_id,
            )
            continue

        result.setdefault(finding.rule_id, []).append(
            str(finding.finding_id)
        )

    return result


def _control_rows(
    compliance_maps: Iterable[ComplianceMap],
    findings_by_rule: Dict[str, List[str]],
    titles: Dict[str, str],
) -> List[dict]:
    """
    Convert ComplianceMap rows into the public CIS/NIST control representation.

    Each ComplianceMap row can represent one CIS control and one NIST
    subcategory, so two public control entries are emitted when both values
    exist.
    """
    controls: List[dict] = []

    for mapping in sorted(
        compliance_maps,
        key=lambda item: item.rule_id,
    ):
        finding_ids = findings_by_rule.get(mapping.rule_id, [])
        status = "FAIL" if finding_ids else "PASS"

        title = titles.get(mapping.rule_id, mapping.rule_id)

        if mapping.cis_control_id:
            controls.append(
                {
                    "control_id": mapping.cis_control_id,
                    "framework": "CIS",
                    "rule_id": mapping.rule_id,
                    "status": status,
                    "title": title,
                    "finding_ids": finding_ids,
                    "remediation": mapping.remediation_steps,
                }
            )

        if mapping.nist_id:
            controls.append(
                {
                    "control_id": mapping.nist_id,
                    "framework": "NIST",
                    "rule_id": mapping.rule_id,
                    "status": status,
                    "title": title,
                    "finding_ids": finding_ids,
                    "remediation": mapping.remediation_steps,
                }
            )

    return controls


def _framework_summary(controls: Iterable[dict]) -> Dict[str, dict]:
    """
    Calculate passed/failed/total counts for CIS and NIST.

    total  = distinct controls in compliance_map
    failed = controls whose rule produced findings
    passed = total - failed
    """
    summary: Dict[str, dict] = {
        "CIS": {"passed": 0, "failed": 0, "total": 0},
        "NIST": {"passed": 0, "failed": 0, "total": 0},
    }

    seen: Set[tuple[str, str, str]] = set()

    for control in controls:
        framework = control["framework"]
        control_id = control["control_id"]
        rule_id = control["rule_id"]

        key = (framework, control_id, rule_id)

        if key in seen:
            continue

        seen.add(key)

        summary[framework]["total"] += 1

        if control["status"] == "FAIL":
            summary[framework]["failed"] += 1
        else:
            summary[framework]["passed"] += 1

    return summary


def build_compliance(
    session: Session,
    findings: Iterable[Finding],
) -> dict:
    """
    Build the complete compliance response data for a scan.

    Parameters
    ----------
    session:
        Database session used to load all compliance-map rows.

    findings:
        Findings belonging to the requested scan.

    Returns
    -------
    dict
        Contains ``frameworks`` and ``controls`` matching the Phase 7 API
        contract.
    """
    findings = list(findings)

    findings_by_rule = _finding_ids_by_rule(findings)

    compliance_maps = session.exec(
        select(ComplianceMap).order_by(ComplianceMap.rule_id)
    ).all()

    titles = _load_rule_titles()

    controls = _control_rows(
        compliance_maps=compliance_maps,
        findings_by_rule=findings_by_rule,
        titles=titles,
    )

    frameworks = _framework_summary(controls)

    return {
        "frameworks": frameworks,
        "controls": controls,
    }