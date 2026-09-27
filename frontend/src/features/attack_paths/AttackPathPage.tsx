import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAttackPaths } from "../../api/scans";
import type { AttackPathEntry, AttackPathNode, Severity } from "../../api/types";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import AttackPathGraph from "./AttackPathGraph";
import AttackPathLegend from "./AttackPathLegend";
import AttackPathDetails from "./AttackPathDetails";

// Same ordering FindingsTable/DashboardPage already use, so "most dangerous
// first" means the same thing everywhere in the app.
const SEVERITY_ORDER: Record<Severity, number> = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
};

/**
 * Member 4 — AttackPathPage (Wave B, Phase 6 frontend)
 *
 * Built against Member 3's published contract and a local mock
 * (frontend/src/mocks/data.ts -> attackPathsById) since the real
 * GET /scans/{id}/attack-paths endpoint doesn't exist yet -- swapping the
 * mock for the real API is just MSW no longer intercepting this route, no
 * change needed here.
 *
 * Not yet wired into a shared scan-detail tab nav (Member 2 hasn't built one
 * yet); reachable directly at /scans/:id/attack-paths in the meantime.
 */
export default function AttackPathPage() {
  const { id } = useParams<{ id: string }>();
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<AttackPathNode | null>(null);

  const query = useQuery({
    queryKey: ["attack-paths", id],
    queryFn: () => getAttackPaths(id as string),
    enabled: Boolean(id),
  });

  const sortedPaths = useMemo(
    () =>
      query.data
        ? [...query.data.paths].sort(
            (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
          )
        : [],
    [query.data],
  );

  const selectedPath: AttackPathEntry | null = useMemo(() => {
    if (!selectedPathId) return null;
    return sortedPaths.find((p) => p.id === selectedPathId) ?? null;
  }, [sortedPaths, selectedPathId]);

  if (query.isLoading) {
    return (
      <Card>
        <Spinner />
      </Card>
    );
  }

  if (query.isError) {
    // Capture to a local so `typeof` narrows the value, not the query object
    // (same fix as DashboardPage.tsx -- narrowing `query.error` directly
    // collapses the union to `never`). The Axios client rejects with a
    // plain string.
    const queryError = query.error;
    const message = typeof queryError === "string" ? queryError : "";
    const isNotFound = message.toLowerCase().includes("not found");
    return (
      <Card>
        {isNotFound ? (
          <p className="font-medium">Scan not found.</p>
        ) : (
          <p className="text-red-700">{message || "Failed to load attack paths."}</p>
        )}
      </Card>
    );
  }

  const data = query.data;
  if (!data) {
    return null;
  }

  if (data.nodes.length === 0) {
    return (
      <Card>
        <p className="text-sm text-gray-500">
          No attack paths found for this scan &mdash; no resource relationships chained
          into an exploit path.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Attack Paths</h2>
            <p className="text-sm text-gray-500">
              {data.paths.length} path{data.paths.length === 1 ? "" : "s"} across{" "}
              {data.nodes.length} resource{data.nodes.length === 1 ? "" : "s"}.
            </p>
          </div>
          <AttackPathLegend />
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-gray-600">Highlight a path:</span>
          <button
            type="button"
            onClick={() => setSelectedPathId(null)}
            aria-pressed={!selectedPathId}
            className={`rounded px-2 py-1 ${
              !selectedPathId ? "bg-blue-600 text-white" : "border text-gray-700"
            }`}
          >
            All
          </button>
          {sortedPaths.map((path) => (
            <button
              key={path.id}
              type="button"
              onClick={() => setSelectedPathId(path.id)}
              aria-pressed={selectedPathId === path.id}
              className={`rounded px-2 py-1 ${
                selectedPathId === path.id ? "bg-blue-600 text-white" : "border text-gray-700"
              }`}
            >
              {path.id} &middot; {path.severity}
            </button>
          ))}
        </div>

        <AttackPathGraph
          nodes={data.nodes}
          links={data.links}
          selectedPath={selectedPath}
          onNodeClick={setSelectedNode}
        />
      </Card>

      {selectedNode && (
        <AttackPathDetails
          node={selectedNode}
          scanId={id as string}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
