import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FindingsTable from "./FindingsTable";
import type { Finding } from "../api/types";

const findings: Finding[] = [
  {
    resource_id: "aws_s3_bucket.public",
    resource_type: "s3_bucket",
    severity: "Critical",
    rule_id: "S3-001",
    message: "Bucket is public",
    risk_score: null,
    is_anomaly: false,
  },
  {
    resource_id: "aws_s3_bucket.logs",
    resource_type: "s3_bucket",
    severity: "Low",
    rule_id: "S3-009",
    message: "Enable access logging",
    risk_score: null,
    is_anomaly: false,
  },
];

const scoredFindings: Finding[] = [
  {
    resource_id: "aws_s3_bucket.low-risk",
    resource_type: "s3_bucket",
    severity: "Low",
    rule_id: "S3-009",
    message: "Enable access logging",
    risk_score: 22,
    is_anomaly: false,
  },
  {
    resource_id: "aws_s3_bucket.high-risk",
    resource_type: "s3_bucket",
    severity: "Critical",
    rule_id: "S3-001",
    message: "Bucket is public",
    risk_score: 92,
    is_anomaly: true,
  },
];

describe("FindingsTable", () => {
  it("filters findings by severity", async () => {
    render(<FindingsTable findings={findings} />);

    // Both rows visible initially.
    expect(screen.getByText("Bucket is public")).toBeInTheDocument();
    expect(screen.getByText("Enable access logging")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/filter by severity/i), "Critical");

    expect(screen.getByText("Bucket is public")).toBeInTheDocument();
    expect(screen.queryByText("Enable access logging")).not.toBeInTheDocument();
  });

  it("renders null risk_score as an em dash", () => {
    render(<FindingsTable findings={findings} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("sorts by risk score, highest first by default", async () => {
    render(<FindingsTable findings={scoredFindings} />);

    await userEvent.click(screen.getByRole("button", { name: /risk score/i }));

    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("aws_s3_bucket.high-risk");
    expect(rows[2]).toHaveTextContent("aws_s3_bucket.low-risk");
  });

  it("shows the Anomaly badge only for anomalous findings", () => {
    render(<FindingsTable findings={scoredFindings} />);

    expect(screen.getByText("Anomaly", { selector: "span" })).toBeInTheDocument();
    expect(screen.getAllByText("No").length).toBe(1);
  });
});
