import { describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AttackPathPage from "./AttackPathPage";
import { renderWithProviders } from "../../test/utils";

// react-force-graph-2d renders to an HTML canvas, which jsdom doesn't
// implement -- mocked here so the page's data/state logic (loading, error,
// empty, path selection, node click-through) can be tested without fighting
// jsdom's missing CanvasRenderingContext2D. Node-selection interactions are
// exercised through the real, always-rendered accessible node list instead
// of this stub, since that's the actual component under test for those
// cases (see AttackPathGraph.tsx).
vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="mock-force-graph" />,
}));

// AttackPathPage takes scanId as a prop (matching CompliancePage) rather
// than reading a route param, since it's rendered as a ScanDetailPage tab,
// not a route, now that Member 2 has wired both feature pages in that way.
function renderFor(scanId: string) {
  return renderWithProviders(<AttackPathPage scanId={scanId} />);
}

function resourceList() {
  return screen.getByRole("group", { name: /select a resource/i });
}

describe("AttackPathPage", () => {
  it("renders the graph, path selector, and legend for a scan with paths", async () => {
    renderFor("1");

    expect(await screen.findByText("Attack Paths")).toBeInTheDocument();
    expect(screen.getByText(/2 paths across 5 resources/i)).toBeInTheDocument();
    expect(screen.getByTestId("mock-force-graph")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /path-1/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /path-2/i })).toBeInTheDocument();
    // Relationship legend (in addition to the severity key).
    expect(screen.getByText("ASSUMES")).toBeInTheDocument();
  });

  it("sorts paths most-severe first", async () => {
    renderFor("1");

    await screen.findByText("Attack Paths");
    const pathButtons = screen.getAllByRole("button", { name: /^path-/i });
    expect(pathButtons.map((b) => b.textContent)).toEqual([
      "path-1 · Critical",
      "path-2 · High",
    ]);
  });

  it("toggles which path is highlighted, and resets on 'All'", async () => {
    renderFor("1");

    await screen.findByText("Attack Paths");
    const allButton = screen.getByRole("button", { name: "All" });
    const path2Button = screen.getByRole("button", { name: /path-2/i });

    expect(allButton).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(path2Button);
    expect(path2Button).toHaveAttribute("aria-pressed", "true");
    expect(allButton).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(allButton);
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(path2Button).toHaveAttribute("aria-pressed", "false");
  });

  it("lists every node as a keyboard-reachable button, independent of the canvas", async () => {
    renderFor("1");

    await screen.findByText("Attack Paths");
    const list = within(resourceList());
    expect(list.getByRole("button", { name: "Public EC2 (web-01)" })).toBeInTheDocument();
    expect(list.getByRole("button", { name: "public-assets (public read)" })).toBeInTheDocument();
    expect(list.getAllByRole("button")).toHaveLength(5);
  });

  it("shows node details, including a related-finding link, on node selection", async () => {
    renderFor("1");

    await screen.findByText("Attack Paths");
    await userEvent.click(
      within(resourceList()).getByRole("button", { name: "public-assets (public read)" }),
    );

    expect(screen.getByText("aws_s3_bucket.public_assets")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view related finding/i })).toHaveAttribute(
      "href",
      "/scans/1",
    );
  });

  it("shows 'no associated finding' for a node with no finding_id", async () => {
    renderFor("1");

    await screen.findByText("Attack Paths");
    await userEvent.click(
      within(resourceList()).getByRole("button", { name: "Public EC2 (web-01)" }),
    );

    expect(screen.getByText("No associated finding")).toBeInTheDocument();
  });

  it("shows a real, non-error empty state when a scan has no attack paths", async () => {
    renderFor("2");

    expect(await screen.findByText(/no attack paths found/i)).toBeInTheDocument();
  });

  it("shows a friendly not-found view for an unknown scan (404)", async () => {
    renderFor("does-not-exist");

    expect(await screen.findByText(/scan not found/i)).toBeInTheDocument();
  });
});
