import { useMemo, useState } from "react";
import type { Finding, Severity } from "../api/types";
import SeverityBadge from "./SeverityBadge";
import AnomalyBadge from "../components/ui/AnomalyBadge";

/**
 * Member 3 — FindingsTable (risk-score sorting and the anomaly badge added
 * by Member 4 once the ML scoring layer started populating those fields).
 *
 * Renders a scan's findings with columns for resource, type, severity, rule,
 * message, risk score, and anomaly status. Supports filtering by severity
 * and sorting by either severity or risk score. risk_score renders as "—"
 * when unscored (nullable in the shared types).
 */

const SEVERITY_ORDER: Record<Severity, number> = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
};

const ALL_SEVERITIES: Severity[] = ["Critical", "High", "Medium", "Low"];

type SortKey = "severity" | "risk";
type SortDirection = "asc" | "desc";

// Severity defaults to ascending (Critical first, matches SEVERITY_ORDER);
// risk defaults to descending (highest risk first) since that's what "sort
// by risk" is for — surfacing the most dangerous findings.
const DEFAULT_DIRECTION: Record<SortKey, SortDirection> = {
  severity: "asc",
  risk: "desc",
};

export default function FindingsTable({ findings }: { findings: Finding[] }) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "All">("All");
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const visibleFindings = useMemo(() => {
    const filtered =
      severityFilter === "All"
        ? findings
        : findings.filter((f) => f.severity === severityFilter);

    return [...filtered].sort((a, b) => {
      const diff =
        sortKey === "severity"
          ? SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
          : (a.risk_score ?? -1) - (b.risk_score ?? -1);
      return sortDirection === "asc" ? diff : -diff;
    });
  }, [findings, severityFilter, sortKey, sortDirection]);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection(DEFAULT_DIRECTION[key]);
    }
  }

  if (findings.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No findings for this scan — nothing to show.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-sm">
        <label htmlFor="severity-filter" className="text-gray-600">
          Filter by severity:
        </label>
        <select
          id="severity-filter"
          className="rounded border px-2 py-1"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value as Severity | "All")}
        >
          <option value="All">All</option>
          {ALL_SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2 pr-4">Resource</th>
            <th className="py-2 pr-4">Type</th>
            <th className="py-2 pr-4">
              <button
                type="button"
                onClick={() => handleSort("severity")}
                className="flex items-center gap-1 font-medium hover:text-gray-900"
              >
                Severity {sortKey === "severity" && (sortDirection === "asc" ? "↑" : "↓")}
              </button>
            </th>
            <th className="py-2 pr-4">Rule</th>
            <th className="py-2 pr-4">Message</th>
            <th className="py-2 pr-4">
              <button
                type="button"
                onClick={() => handleSort("risk")}
                className="flex items-center gap-1 font-medium hover:text-gray-900"
              >
                Risk score {sortKey === "risk" && (sortDirection === "asc" ? "↑" : "↓")}
              </button>
            </th>
            <th className="py-2 pr-4">Anomaly</th>
          </tr>
        </thead>
        <tbody>
          {visibleFindings.map((finding) => (
            <tr key={`${finding.resource_id}-${finding.rule_id}`} className="border-b">
              <td className="py-2 pr-4 font-mono text-xs">{finding.resource_id}</td>
              <td className="py-2 pr-4">{finding.resource_type}</td>
              <td className="py-2 pr-4">
                <SeverityBadge severity={finding.severity} />
              </td>
              <td className="py-2 pr-4">{finding.rule_id}</td>
              <td className="py-2 pr-4">{finding.message}</td>
              <td className="py-2 pr-4">{finding.risk_score ?? "—"}</td>
              <td className="py-2 pr-4">
                <AnomalyBadge isAnomaly={finding.is_anomaly} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
