import type { ScanDetail, ScanSummary } from "../api/types";

// Mock data mirrors the real Phase 2 API shape: scan_type is the backend enum
// ("STATIC" | "LIVE"), timestamps are ISO strings, and risk_score stays null
// until Phase 5 populates it.
export const scans: ScanSummary[] = [
  {
    scan_id: "1",
    filename: "prod-aws-config.json",
    scan_type: "STATIC",
    status: "COMPLETED",
    timestamp: "2026-07-10T14:30:00Z",
  },
  {
    scan_id: "2",
    filename: "staging-infra.yaml",
    scan_type: "STATIC",
    status: "COMPLETED",
    timestamp: "2026-07-09T09:15:00Z",
  },
  {
    scan_id: "3",
    filename: "Live Cloud Account",
    scan_type: "LIVE",
    status: "COMPLETED",
    timestamp: "2026-07-11T10:00:00Z",
  },
];

export const scanDetailsById: Record<string, ScanDetail> = {
  "1": {
    ...scans[0],
    findings: [
      {
        resource_id: "aws_s3_bucket.public_assets",
        resource_type: "s3_bucket",
        severity: "Critical",
        rule_id: "S3-001",
        message: "Disable public read access on the S3 bucket.",
        risk_score: null,
        is_anomaly: false,
      },
      {
        resource_id: "aws_security_group.web",
        resource_type: "security_group",
        severity: "High",
        rule_id: "SG-014",
        message: "Restrict inbound 0.0.0.0/0 on port 22.",
        risk_score: null,
        is_anomaly: false,
      },
      {
        resource_id: "aws_iam_policy.admin",
        resource_type: "iam_policy",
        severity: "Medium",
        rule_id: "IAM-007",
        message: "Avoid wildcard actions in IAM policies.",
        risk_score: null,
        is_anomaly: false,
      },
    ],
  },
  "2": {
    ...scans[1],
    findings: [
      {
        resource_id: "aws_s3_bucket.logs",
        resource_type: "s3_bucket",
        severity: "Low",
        rule_id: "S3-009",
        message: "Enable access logging on the bucket.",
        risk_score: null,
        is_anomaly: false,
      },
    ],
  },
  "3": {
    ...scans[2],
    findings: [
      {
       resource_id: "example-bucket",
       resource_type: "s3_bucket",
       severity: "High",
       rule_id: "S3-001",
       message: "Disable public read access on the S3 bucket.",
       risk_score: null,
       is_anomaly: false,
     },
     {
       resource_id: "sg-example",
       resource_type: "security_group",
       severity: "Medium",
       rule_id: "SG-014",
       message: "Restrict inbound access from 0.0.0.0/0.",
       risk_score: null,
       is_anomaly: false,
     },
   ],
 },
};
