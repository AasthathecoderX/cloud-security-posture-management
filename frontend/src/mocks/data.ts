import type { AttackPathResponse, ScanDetail, ScanSummary } from "../api/types";

// Mock data mirrors the real Phase 2 API shape: scan_type is the backend enum
// ("STATIC" | "LIVE"), timestamps are ISO strings. risk_score/is_anomaly are
// populated to mirror what backend/src/ml/scorer.py now returns for every
// scan (Wave A, Member 4) -- a heuristic stand-in until Member 3's trained
// model lands; only the numbers are illustrative, not the real model output.
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
        risk_score: 92,
        is_anomaly: true,
      },
      {
        resource_id: "aws_security_group.web",
        resource_type: "security_group",
        severity: "High",
        rule_id: "SG-014",
        message: "Restrict inbound 0.0.0.0/0 on port 22.",
        risk_score: 74,
        is_anomaly: false,
      },
      {
        resource_id: "aws_iam_policy.admin",
        resource_type: "iam_policy",
        severity: "Medium",
        rule_id: "IAM-007",
        message: "Avoid wildcard actions in IAM policies.",
        risk_score: 48,
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
        risk_score: 22,
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
       risk_score: 71,
       is_anomaly: false,
     },
     {
       resource_id: "sg-example",
       resource_type: "security_group",
       severity: "Medium",
       rule_id: "SG-014",
       message: "Restrict inbound access from 0.0.0.0/0.",
       risk_score: 46,
       is_anomaly: false,
     },
   ],
 },
};

// Phase 6 / Wave B — Attack-Path mock data (Member 4, scaffolded ahead of
// Member 3's real endpoint). Illustrates the target contract's canonical
// "exposed instance -> assumed role -> over-permissioned policy -> data
// store" chain; the `instance`/`iam_role` node types don't exist in the real
// collector yet (see the Wave B plan's Day 0-2 prerequisite), so this is
// what the graph *will* show once that data exists, not what it shows today.
// finding_id values are resource_ids (see the AttackPathNode comment in
// api/types.ts) so click-through already works against real Finding data.
export const attackPathsById: Record<string, AttackPathResponse> = {
  "1": {
    scan_id: "1",
    nodes: [
      {
        id: "sg-web",
        type: "security_group",
        label: "web (open ingress)",
        severity: "High",
        risk_score: 74,
        finding_id: "aws_security_group.web",
      },
      {
        id: "i-0abc123",
        type: "instance",
        label: "Public EC2 (web-01)",
        severity: "High",
        risk_score: 81,
        finding_id: null,
      },
      {
        id: "role-web-app",
        type: "iam_role",
        label: "web-app-role",
        severity: "Medium",
        risk_score: 52,
        finding_id: null,
      },
      {
        id: "aws_iam_policy.admin",
        type: "iam_policy",
        label: "admin-policy (wildcard actions)",
        severity: "Medium",
        risk_score: 48,
        finding_id: "aws_iam_policy.admin",
      },
      {
        id: "aws_s3_bucket.public_assets",
        type: "s3_bucket",
        label: "public-assets (public read)",
        severity: "Critical",
        risk_score: 92,
        finding_id: "aws_s3_bucket.public_assets",
      },
    ],
    links: [
      { source: "sg-web", target: "i-0abc123", relationship: "EXPOSES" },
      { source: "i-0abc123", target: "role-web-app", relationship: "ASSUMES" },
      { source: "role-web-app", target: "aws_iam_policy.admin", relationship: "HAS_PERMISSION" },
      { source: "aws_iam_policy.admin", target: "aws_s3_bucket.public_assets", relationship: "ACCESSES" },
    ],
    paths: [
      {
        id: "path-1",
        nodes: [
          "sg-web",
          "i-0abc123",
          "role-web-app",
          "aws_iam_policy.admin",
          "aws_s3_bucket.public_assets",
        ],
        severity: "Critical",
      },
      // A second, shorter path sharing the same entry point -- also gives
      // the UI something real to sort by severity (High < Critical).
      {
        id: "path-2",
        nodes: ["sg-web", "i-0abc123"],
        severity: "High",
      },
    ],
  },

  // Deliberately empty: a single Low-severity logging finding doesn't chain
  // into anything. Exercises the "no attack paths found" state, which the
  // Wave B plan calls out as a valid, tested outcome -- not an error.
  "2": {
    scan_id: "2",
    nodes: [],
    links: [],
    paths: [],
  },

  "3": {
    scan_id: "3",
    nodes: [
      {
        id: "sg-example",
        type: "security_group",
        label: "sg-example (open ingress)",
        severity: "Medium",
        risk_score: 46,
        finding_id: "sg-example",
      },
      {
        id: "i-live-01",
        type: "instance",
        label: "Live EC2 instance",
        severity: "High",
        risk_score: 71,
        finding_id: null,
      },
      {
        id: "example-bucket",
        type: "s3_bucket",
        label: "example-bucket (public read)",
        severity: "High",
        risk_score: 71,
        finding_id: "example-bucket",
      },
    ],
    links: [
      { source: "sg-example", target: "i-live-01", relationship: "EXPOSES" },
      { source: "i-live-01", target: "example-bucket", relationship: "ACCESSES" },
    ],
    paths: [
      {
        id: "path-1",
        nodes: ["sg-example", "i-live-01", "example-bucket"],
        severity: "High",
      },
    ],
  },
};
