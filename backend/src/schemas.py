"""
Pydantic schemas for the CSPM API.

These models define the request and response formats used by the API and serve
as the contract between the backend endpoints and clients. Enum labels follow
docs/schema.md; ``from_attributes`` lets responses be built directly from the
SQLModel ORM objects in models.py.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ScanStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScanType(str, Enum):
    STATIC = "STATIC"
    LIVE = "LIVE"


# Supported upload file types (importable constant for the endpoints layer).
ALLOWED_EXTENSIONS = {".json", ".yaml", ".yml"}


class FindingResponse(BaseModel):
    """Represents a single security finding."""

    model_config = ConfigDict(from_attributes=True)

    finding_id: UUID = Field(
        description=(
            "Unique identifier of this finding. Already used internally by "
            "the Phase 7 compliance engine (compliance/engine.py); exposed "
            "here so other consumers (e.g. the Phase 6 attack-path API) "
            "have a stable id to reference instead of resource_id."
        ),
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    resource_id: str = Field(
        description="Unique identifier of the affected resource",
        examples=["bucket-001"],
    )
    resource_type: str = Field(
        description="Type of cloud resource",
        examples=["s3_bucket"],
    )
    severity: Severity = Field(
        description="Severity of the finding",
        examples=["High"],
    )
    rule_id: str = Field(
        description="Security rule that generated the finding",
        examples=["CIS-AWS-001"],
    )
    message: str = Field(
        description="Remediation or explanation of the finding",
        examples=["Disable public read access on the S3 bucket."],
    )
    risk_score: Optional[int] = Field(
        default=None,
        description="ML-assigned risk score (0-100); populated in a later phase",
        examples=[87],
    )
    is_anomaly: bool = Field(
        default=False,
        description="Whether anomaly detection flagged this finding",
        examples=[False],
    )


class UploadResponse(BaseModel):
    """Response returned after uploading and scanning a configuration."""

    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID = Field(
        description="Unique identifier of the created scan",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: ScanStatus = Field(
        description="Current scan status",
        examples=["COMPLETED"],
    )
    findings_count: int = Field(
        description="Number of findings detected",
        examples=[3],
    )


class ScanSummary(BaseModel):
    """Summary information about a scan."""

    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID = Field(
        description="Unique identifier of the scan",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    filename: str = Field(
        description="Uploaded configuration filename",
        examples=["aws-config.yaml"],
    )
    scan_type: ScanType = Field(
        description="Type of scan",
        examples=["STATIC"],
    )
    status: ScanStatus = Field(
        description="Current scan status",
        examples=["COMPLETED"],
    )
    timestamp: datetime = Field(
        description="Time when the scan was created",
    )


class ScanDetail(BaseModel):
    """Detailed information about a scan, including its findings."""

    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID = Field(
        description="Unique identifier of the scan",
    )
    filename: str = Field(
        description="Uploaded configuration filename",
    )
    scan_type: ScanType = Field(
        description="Type of scan",
    )
    status: ScanStatus = Field(
        description="Current scan status",
    )
    timestamp: datetime = Field(
        description="Time when the scan was created",
    )
    findings: list[FindingResponse] = Field(
        description="Security findings generated during the scan",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(
        description="Description of the error",
        examples=["Unsupported file type."],
    )
