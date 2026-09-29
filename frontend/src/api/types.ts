export type Severity = "Low" | "Medium" | "High" | "Critical";

export type ScanStatus =
  | "IN_PROGRESS"
  | "COMPLETED"
  | "FAILED";

export type ScanType = "STATIC" | "LIVE";

export interface Finding {
  resource_id: string;
  resource_type: string;
  severity: Severity;
  rule_id: string;
  message: string;
  risk_score: number | null;
  is_anomaly: boolean;
}

export interface ScanSummary {
  scan_id: string;
  filename: string;
  scan_type: ScanType;
  status: ScanStatus;
  timestamp: string;
}

export interface ScanDetail extends ScanSummary {
  findings: Finding[];
}

export interface UploadResponse {
  scan_id: string;
  status: ScanStatus;
  findings_count: number;
}

export interface ErrorResponse {
  detail: string;
}

// Phase 6 / Wave B — Attack-Path API (Contract 2). The backend endpoint
// (GET /scans/{id}/attack-paths) doesn't exist yet; these types match the
// contract published in guides/wave B/Wave_B_Detailed_Execution_Plan.md so
// the frontend can be built against a mock now and swapped to the real
// endpoint without a type change once Member 3 ships it.
export type AttackPathResourceType =
  | "instance"
  | "iam_role"
  | "iam_policy"
  | "s3_bucket"
  | "security_group";

export type AttackPathRelationship =
  | "ASSUMES"
  | "HAS_PERMISSION"
  | "ACCESSES"
  | "EXPOSES";

export interface AttackPathNode {
  id: string;
  type: AttackPathResourceType;
  label: string;
  severity: Severity;
  risk_score: number | null;
  // Stand-in until FindingResponse carries a real finding_id (it doesn't
  // today -- see Finding above): populated with the finding's resource_id,
  // the only stable identifier the app currently exposes for a finding.
  finding_id: string | null;
}

export interface AttackPathLink {
  source: string;
  target: string;
  relationship: AttackPathRelationship;
}

export interface AttackPathEntry {
  id: string;
  nodes: string[];
  severity: Severity;
}

export interface AttackPathResponse {
  scan_id: string;
  nodes: AttackPathNode[];
  links: AttackPathLink[];
  paths: AttackPathEntry[];
}

export type ComplianceStatus = "PASS" | "FAIL";

export type ComplianceFramework = "CIS" | "NIST";

export interface FrameworkSummary {
  passed: number;
  failed: number;
  total: number;
}

export interface ComplianceControl {
  control_id: string;
  framework: ComplianceFramework;
  rule_id: string;
  status: ComplianceStatus;
  title: string;
  finding_ids: string[];
  remediation: string;
}

export interface ComplianceResponse {
  scan_id: string;
  frameworks: Record<ComplianceFramework, FrameworkSummary>;
  controls: ComplianceControl[];
}