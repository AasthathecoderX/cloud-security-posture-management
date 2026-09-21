"""
Mock response for the Phase 7 compliance API.

This mirrors the public API contract so the frontend can be developed before
the real endpoint is integrated.
"""

MOCK_COMPLIANCE_RESPONSE = {
    "scan_id": "550e8400-e29b-41d4-a716-446655440000",
    "frameworks": {
        "CIS": {
            "passed": 3,
            "failed": 2,
            "total": 5,
        },
        "NIST": {
            "passed": 3,
            "failed": 2,
            "total": 5,
        },
    },
    "controls": [
        {
            "control_id": "2.1.5",
            "framework": "CIS",
            "rule_id": "CIS-AWS-001",
            "status": "FAIL",
            "title": "S3 Bucket Public Read Access",
            "finding_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
            ],
            "remediation": (
                "Disable public read access and enable S3 Block Public "
                "Access on the bucket."
            ),
        },
        {
            "control_id": "5.2",
            "framework": "CIS",
            "rule_id": "CIS-AWS-002",
            "status": "PASS",
            "title": "Security Group Open Ingress",
            "finding_ids": [],
            "remediation": (
                "Restrict inbound access to trusted IP ranges instead "
                "of 0.0.0.0/0."
            ),
        },
        {
            "control_id": "1.16",
            "framework": "CIS",
            "rule_id": "CIS-AWS-003",
            "status": "FAIL",
            "title": "IAM Policy Wildcard Action",
            "finding_ids": [
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "remediation": (
                "Replace wildcard actions with specific actions following "
                "the principle of least privilege."
            ),
        },
        {
            "control_id": "2.1.1",
            "framework": "CIS",
            "rule_id": "CIS-AWS-004",
            "status": "PASS",
            "title": "S3 Bucket Encryption Disabled",
            "finding_ids": [],
            "remediation": (
                "Enable default server-side encryption (SSE-S3 or SSE-KMS) "
                "on the bucket."
            ),
        },
        {
            "control_id": "1.16",
            "framework": "CIS",
            "rule_id": "CIS-AWS-005",
            "status": "PASS",
            "title": "IAM Policy Wildcard Principal",
            "finding_ids": [],
            "remediation": (
                "Remove wildcard principals; grant access only to specific, "
                "trusted principals."
            ),
        },
        {
            "control_id": "PR.AC-3",
            "framework": "NIST",
            "rule_id": "CIS-AWS-001",
            "status": "FAIL",
            "title": "S3 Bucket Public Read Access",
            "finding_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
            ],
            "remediation": (
                "Disable public read access and enable S3 Block Public "
                "Access on the bucket."
            ),
        },
        {
            "control_id": "PR.AC-5",
            "framework": "NIST",
            "rule_id": "CIS-AWS-002",
            "status": "PASS",
            "title": "Security Group Open Ingress",
            "finding_ids": [],
            "remediation": (
                "Restrict inbound access to trusted IP ranges instead "
                "of 0.0.0.0/0."
            ),
        },
        {
            "control_id": "PR.AC-4",
            "framework": "NIST",
            "rule_id": "CIS-AWS-003",
            "status": "FAIL",
            "title": "IAM Policy Wildcard Action",
            "finding_ids": [
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            "remediation": (
                "Replace wildcard actions with specific actions following "
                "the principle of least privilege."
            ),
        },
        {
            "control_id": "PR.DS-1",
            "framework": "NIST",
            "rule_id": "CIS-AWS-004",
            "status": "PASS",
            "title": "S3 Bucket Encryption Disabled",
            "finding_ids": [],
            "remediation": (
                "Enable default server-side encryption (SSE-S3 or SSE-KMS) "
                "on the bucket."
            ),
        },
        {
            "control_id": "PR.AC-4",
            "framework": "NIST",
            "rule_id": "CIS-AWS-005",
            "status": "PASS",
            "title": "IAM Policy Wildcard Principal",
            "finding_ids": [],
            "remediation": (
                "Remove wildcard principals; grant access only to specific, "
                "trusted principals."
            ),
        },
    ],
}