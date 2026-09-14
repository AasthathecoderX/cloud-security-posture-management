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