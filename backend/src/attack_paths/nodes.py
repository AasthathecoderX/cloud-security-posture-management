from typing import Any, Dict, Optional

from models import Finding


def build_node(
    resource: Dict[str, Any],
    finding: Optional[Finding] = None,
) -> Dict[str, Any]:
    """Convert a normalized resource into an API-safe attack-path node."""

    resource_id = str(resource["resource_id"])
    resource_type = str(resource["resource_type"])

    severity = None
    risk_score = None
    finding_id = None

    if finding is not None:
        severity = finding.severity.value
        risk_score = finding.risk_score
        finding_id = str(finding.finding_id)

    return {
        "id": resource_id,
        "type": resource_type,
        "label": _build_label(resource),
        "severity": severity,
        "risk_score": risk_score,
        "finding_id": finding_id,
    }


def _build_label(resource: Dict[str, Any]) -> str:
    """Create a readable label without exposing provider-specific internals."""

    resource_type = resource.get("resource_type", "resource")
    resource_id = resource.get("resource_id", "unknown")

    labels = {
        "ec2_instance": "EC2 Instance",
        "iam_role": "IAM Role",
        "iam_policy": "IAM Policy",
        "s3_bucket": "S3 Bucket",
        "security_group": "Security Group",
    }

    prefix = labels.get(resource_type, resource_type)

    return f"{prefix} ({resource_id})"