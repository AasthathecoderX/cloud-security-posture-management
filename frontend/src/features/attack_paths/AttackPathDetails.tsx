import { Link } from "react-router-dom";
import type { AttackPathNode } from "../../api/types";
import Card from "../../components/ui/Card";
import SeverityBadge from "../../pages/SeverityBadge";

/**
 * Member 4 — AttackPathDetails
 *
 * Shown for whichever node the user clicked in the graph. Links back to the
 * scan's findings view (there's no separate Findings tab yet -- ScanDetailPage
 * *is* the findings view today) using the node's finding_id, which is
 * currently just the finding's resource_id (see the AttackPathNode comment
 * in api/types.ts).
 */
export default function AttackPathDetails({
  node,
  scanId,
  onClose,
}: {
  node: AttackPathNode;
  scanId: string;
  onClose: () => void;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-gray-500">{node.id}</p>
          <h3 className="font-medium">{node.label}</h3>
          <p className="text-sm text-gray-500">{node.type}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-gray-500 hover:text-gray-900"
        >
          Close
        </button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        <SeverityBadge severity={node.severity} />
        {node.risk_score != null && (
          <span className="font-semibold">Risk {node.risk_score}</span>
        )}
        {node.finding_id ? (
          <Link to={`/scans/${scanId}`} className="text-blue-600 hover:underline">
            View related finding &rarr;
          </Link>
        ) : (
          <span className="text-gray-400">No associated finding</span>
        )}
      </div>
    </Card>
  );
}
