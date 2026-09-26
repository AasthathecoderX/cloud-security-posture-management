"""
Phase 7 Compliance API routes.

Endpoint:
    GET /scans/{scan_id}/compliance
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from db import get_session
from models import User
from routes import _load_owned_scan, get_current_user
from schemas import ErrorResponse
from compliance.engine import build_compliance
from compliance.schemas import ComplianceResponse


router = APIRouter(
    tags=["compliance"],
)


@router.get(
    "/scans/{scan_id}/compliance",
    response_model=ComplianceResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Scan not found",
        }
    },
)
def get_scan_compliance(
    scan_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ComplianceResponse:
    """
    Return CIS/NIST compliance status for a scan.

    The scan is first loaded through the existing IDOR-safe helper.
    Findings are then aggregated using their existing ComplianceMap
    relationship.
    """
    scan = _load_owned_scan(
        scan_id=scan_id,
        session=session,
        user=user,
    )

    result = build_compliance(
        session=session,
        findings=scan.findings,
    )

    return ComplianceResponse(
        scan_id=scan.scan_id,
        **result,
    )