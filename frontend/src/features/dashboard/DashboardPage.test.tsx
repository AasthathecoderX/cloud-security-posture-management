import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import DashboardPage from "./DashboardPage";
import { renderWithProviders } from "../../test/utils";
import { server } from "../../test/setup";

describe("DashboardPage", () => {
  it("aggregates findings from the mock data into the charts", async () => {
    renderWithProviders(<DashboardPage />);

    // Mock data: scan 1 has 3 findings, scan 2 has 1, scan 3 has 2 -> 6 across 3 scans.
    expect(await screen.findByText(/6 findings across 3 scans/i)).toBeInTheDocument();

    expect(screen.getByText("Findings by severity")).toBeInTheDocument();
    expect(screen.getByText("Findings by resource type")).toBeInTheDocument();

    // Severity summary derived from the findings.
    expect(screen.getByText("Critical: 1")).toBeInTheDocument();
    expect(screen.getByText("High: 2")).toBeInTheDocument();
    expect(screen.getByText("Medium: 2")).toBeInTheDocument();
    expect(screen.getByText("Low: 1")).toBeInTheDocument();
  });

  it("shows the highest-risk finding first in the Top Risks panel", async () => {
    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText("Top risks")).toBeInTheDocument();
    // Highest risk_score in the mock data (92) belongs to this resource.
    const topRiskItem = screen
      .getByText("aws_s3_bucket.public_assets")
      .closest("li");
    expect(topRiskItem).not.toBeNull();
    expect(topRiskItem).toHaveTextContent("92");
    expect(topRiskItem).toHaveTextContent("Anomaly");
    expect(
      within(topRiskItem as HTMLElement).getByRole("link", { name: "View scan" }),
    ).toHaveAttribute("href", "/scans/1");
  });

  it("shows an empty state when there are no scans", async () => {
    server.use(http.get("*/scans", () => HttpResponse.json([])));

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText(/nothing to show yet/i)).toBeInTheDocument();
  });
});
