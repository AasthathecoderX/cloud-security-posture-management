import { useMemo, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { AttackPathEntry, AttackPathLink, AttackPathNode, Severity } from "../../api/types";

/**
 * Member 4 — AttackPathGraph
 *
 * Renders Member 3's node/link JSON (Contract 2) as an interactive force
 * graph. Severity coloring mirrors Member 1's Badge / the Dashboard's
 * SEVERITY_COLORS so this reads as the same visual language as the rest of
 * the app. When a path is selected, everything outside it dims instead of
 * being hidden, so the graph's overall shape stays visible for context.
 *
 * The canvas has no native focus/selection model -- a mouse is the only way
 * to pick a node in the graph itself. The button list below it is a real,
 * keyboard-and-screen-reader-reachable second way to select the same nodes,
 * not a decoration; it's always visible rather than hidden until focus, so
 * it also works for anyone who'd simply rather read than parse a force
 * layout.
 */

const SEVERITY_COLORS: Record<Severity, string> = {
  Low: "#6b7280",
  Medium: "#eab308",
  High: "#f97316",
  Critical: "#dc2626",
};

const DIMMED = "#d1d5db"; // gray-300

// react-force-graph mutates link.source/target from the input string ids
// into live node object references once the simulation starts, so a link's
// endpoint may be either shape depending on render timing.
function linkEndpointId(endpoint: string | { id: string }): string {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}

type Props = {
  nodes: AttackPathNode[];
  links: AttackPathLink[];
  selectedPath: AttackPathEntry | null;
  onNodeClick: (node: AttackPathNode) => void;
};

export default function AttackPathGraph({ nodes, links, selectedPath, onNodeClick }: Props) {
  const fgRef = useRef<unknown>(null);

  const highlightedNodeIds = useMemo(
    () => new Set(selectedPath?.nodes ?? []),
    [selectedPath],
  );

  const graphData = useMemo(
    () => ({
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({ ...l })),
    }),
    [nodes, links],
  );

  function isNodeHighlighted(nodeId: string) {
    return !selectedPath || highlightedNodeIds.has(nodeId);
  }

  function isLinkHighlighted(link: AttackPathLink) {
    if (!selectedPath) return true;
    return (
      highlightedNodeIds.has(linkEndpointId(link.source)) &&
      highlightedNodeIds.has(linkEndpointId(link.target))
    );
  }

  return (
    <div>
      <div
        style={{ width: "100%", height: 420 }}
        className="overflow-hidden rounded border"
        data-testid="attack-path-graph"
      >
        <ForceGraph2D
          ref={fgRef as never}
          graphData={graphData}
          nodeId="id"
          nodeLabel={(node) => {
            const n = node as unknown as AttackPathNode;
            const risk = n.risk_score != null ? ` · risk ${n.risk_score}` : "";
            return `${n.label} · ${n.type}${risk}`;
          }}
          nodeColor={(node) => {
            const n = node as unknown as AttackPathNode;
            return isNodeHighlighted(n.id) ? SEVERITY_COLORS[n.severity] : DIMMED;
          }}
          linkColor={(link) => (isLinkHighlighted(link as unknown as AttackPathLink) ? "#374151" : DIMMED)}
          linkWidth={(link) => (isLinkHighlighted(link as unknown as AttackPathLink) ? 2.5 : 1)}
          linkLabel={(link) => (link as unknown as AttackPathLink).relationship}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          onNodeClick={(node) => onNodeClick(node as unknown as AttackPathNode)}
          cooldownTicks={100}
        />
      </div>

      <div className="mt-3" role="group" aria-label="Select a resource">
        <p className="mb-1.5 text-xs font-medium text-gray-500">
          Resources in this graph
        </p>
        <ul className="flex flex-wrap gap-1.5">
          {nodes.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                onClick={() => onNodeClick(node)}
                className="flex items-center gap-1.5 rounded border px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
              >
                <span
                  aria-hidden="true"
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: isNodeHighlighted(node.id)
                      ? SEVERITY_COLORS[node.severity]
                      : DIMMED,
                  }}
                />
                {node.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
