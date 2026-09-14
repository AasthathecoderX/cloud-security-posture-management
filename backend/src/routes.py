"""
FastAPI endpoints (Phase 2, Member 3).

Wraps the Phase 1 SecureParser + RuleEngine over HTTP and persists results:

- POST /scans/upload           parse -> evaluate -> store, returns UploadResponse
- GET  /scans                  list the caller's scans
- GET  /scans/{scan_id}        one scan with its findings
- GET  /scans/{scan_id}/findings   findings for one scan

Every query is scoped to the current user (placeholder dependency until auth in
Phase 8). A scan that does not belong to the caller returns 404, not 403, so the
existence of other users' scans is not leaked (IDOR defence).
"""

import os
import re
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from db import get_session
from models import (
    Finding,
    Scan,
    ScanStatus,
    ScanType,
    Severity,
    User,
    UserRole,
)
from parser import MAX_FILE_SIZE, SecureParser
from rule_engine import RuleEngine
from schemas import (
    ALLOWED_EXTENSIONS,
    FindingResponse,
    ScanDetail,
    ScanSummary,
    UploadResponse,
)
from cloud.collector import collect_cloud_resources

# Rules live at the repository root (../../rules from this file). Allow an env
# override so the API can be run/packaged from a different layout.
_DEFAULT_RULES_DIR = Path(__file__).resolve().parents[2] / "rules"
RULES_DIR = os.getenv("RULES_DIR", str(_DEFAULT_RULES_DIR))

# Load the engine + parser once at import time (rules are read-only).
_engine = RuleEngine(rules_directory=RULES_DIR)
_parser = SecureParser()

# Placeholder identity until authentication lands in Phase 8. Tests override
# this dependency to simulate different users.
_DEV_USER_EMAIL = "dev@local"

# Strips directory components / control characters from an untrusted filename.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_MAX_FILENAME_LEN = 255


def _safe_filename(raw: str) -> str:
    """Reduce an untrusted upload filename to a safe, stored basename.

    Defence-in-depth against stored XSS / header/log injection when the name is
    later reflected by clients: keep only the final path component, drop control
    characters (including newlines), and cap the length. Output encoding in the
    UI remains the primary XSS control.
    """
    name = Path(raw).name
    name = _CONTROL_CHARS.sub("", name)
    return name[:_MAX_FILENAME_LEN]


def get_current_user(session: Session = Depends(get_session)) -> User:
    """Return the current user.

    Until authentication lands (Phase 8) this is a placeholder that, in
    non-production environments only, get-or-creates a least-privilege
    development user. In production it refuses to fabricate an identity.
    """
    user = session.exec(
        select(User).where(User.email == _DEV_USER_EMAIL)
    ).first()
    if user is not None:
        return user

    if os.getenv("CSPM_ENV", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = User(
        email=_DEV_USER_EMAIL,
        password_hash="!",  # not a usable credential; auth arrives in Phase 8
        role=UserRole.VIEWER,  # least privilege for the placeholder identity
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


router = APIRouter(tags=["scans"])


def _load_owned_scan(
    scan_id: UUID, session: Session, user: User
) -> Scan:
    """Fetch a scan scoped to the caller, or raise 404 (IDOR-safe)."""
    scan = session.get(Scan, scan_id)
    if scan is None or scan.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found."
        )
    return scan


@router.post(
    "/scans/upload",
    response_model=UploadResponse,
    responses={400: {"description": "Invalid upload or unparseable configuration"}},
)
async def upload_scan(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload a JSON/YAML cloud config, scan it, and store scan + findings."""
    filename = _safe_filename(file.filename or "")
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{extension or filename}'. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}."
            ),
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File exceeds maximum size of "
                f"{MAX_FILE_SIZE // (1024 * 1024)} MB."
            ),
        )

    # SecureParser reads from disk (size/depth/alias defences); write the upload
    # to a temp file that preserves the extension, then always clean it up.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=extension, delete=False
        ) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        try:
            data = _parser.parse(tmp_path)
        except (ValueError, TimeoutError, RecursionError) as exc:
            # Turn bad input into a clean 400 (never a 500 stack trace).
            # RecursionError guards against deeply-nested JSON/YAML that blows
            # the interpreter stack inside the underlying loader.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse configuration: {exc}",
            )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    findings_data = _engine.evaluate(data)

    scan = Scan(
        user_id=user.user_id,
        filename=filename,
        scan_type=ScanType.STATIC,
        status=ScanStatus.COMPLETED,
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)

    for item in findings_data:
        session.add(
            Finding(
                scan_id=scan.scan_id,
                resource_id=item["resource_id"],
                resource_type=item["resource_type"],
                severity=Severity(item["severity"]),
                rule_id=item["rule_id"],
                message=item["message"],
            )
        )
    session.commit()

    return UploadResponse(
        scan_id=scan.scan_id,
        status=scan.status,
        findings_count=len(findings_data),
    )

@router.post(
    "/scans/cloud",
    response_model=UploadResponse,
    responses={502: {"description": "Cloud collection failed"}},
)
def scan_cloud_account(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Collect live cloud resources, evaluate them, and store the scan."""

    try:
        resources = collect_cloud_resources()
    except Exception:
        # Do not expose internal cloud/SDK details to the client.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloud resource collection failed.",
        )

    findings_data = _engine.evaluate(resources)

    scan = Scan(
        user_id=user.user_id,
        filename="Live Cloud Account",
        scan_type=ScanType.LIVE,
        status=ScanStatus.COMPLETED,
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)

    for item in findings_data:
        session.add(
            Finding(
                scan_id=scan.scan_id,
                resource_id=item["resource_id"],
                resource_type=item["resource_type"],
                severity=Severity(item["severity"]),
                rule_id=item["rule_id"],
                message=item["message"],
            )
        )

    session.commit()

    return UploadResponse(
        scan_id=scan.scan_id,
        status=scan.status,
        findings_count=len(findings_data),
    )

@router.get("/scans", response_model=list[ScanSummary])
def list_scans(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[Scan]:
    """List the caller's scans, newest first."""
    return session.exec(
        select(Scan)
        .where(Scan.user_id == user.user_id)
        .order_by(Scan.timestamp.desc())
    ).all()


@router.get(
    "/scans/{scan_id}",
    response_model=ScanDetail,
    responses={404: {"description": "Scan not found"}},
)
def get_scan(
    scan_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Scan:
    """Return one scan (scoped to the caller) with its findings."""
    return _load_owned_scan(scan_id, session, user)


@router.get(
    "/scans/{scan_id}/findings",
    response_model=list[FindingResponse],
    responses={404: {"description": "Scan not found"}},
)
def get_scan_findings(
    scan_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[Finding]:
    """Return the findings for one scan (scoped to the caller)."""
    scan = _load_owned_scan(scan_id, session, user)
    return scan.findings
