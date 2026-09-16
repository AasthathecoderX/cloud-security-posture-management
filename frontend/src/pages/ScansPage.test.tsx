import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import ScansPage from "./ScansPage";
import { renderWithProviders } from "../test/utils";
import { server } from "../test/setup";

describe("ScansPage", () => {
  it("renders the scans returned by the API, newest first", async () => {
    renderWithProviders(<ScansPage />);

    const firstScan = await screen.findByRole("link", { name: "prod-aws-config.json" });
    expect(firstScan).toHaveAttribute("href", "/scans/1");
    expect(screen.getByRole("link", { name: "staging-infra.yaml" })).toBeInTheDocument();

    // Newest-first: the 2026-07-11 live scan, then 07-10, then 07-09.
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Live Cloud Account");
    expect(rows[2]).toHaveTextContent("prod-aws-config.json");
    expect(rows[3]).toHaveTextContent("staging-infra.yaml");
  });

  it("shows an empty state when there are no scans", async () => {
    server.use(http.get("*/scans", () => HttpResponse.json([])));

    renderWithProviders(<ScansPage />);

    expect(await screen.findByText(/no scans yet/i)).toBeInTheDocument();
  });
});
