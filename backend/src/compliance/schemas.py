"""
Pydantic schemas for the Phase 7 compliance API.

The compliance endpoint reports rule-level compliance status:
a control is FAIL when its rule produced one or more findings in the scan;
otherwise it is PASS.

This does not mean every individual resource was verified against the control.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class FrameworkSummary(BaseModel):
    """Aggregated control counts for one compliance framework."""

    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    total: int = Field(ge=0)


class ComplianceControl(BaseModel):
    """One CIS or NIST control and its status for a scan."""

    control_id: str
    framework: str
    rule_id: str
    status: ComplianceStatus
    title: str
    finding_ids: List[str]
    remediation: str


class ComplianceResponse(BaseModel):
    """Response returned by GET /scans/{scan_id}/compliance."""

    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    frameworks: Dict[str, FrameworkSummary]
    controls: List[ComplianceControl]