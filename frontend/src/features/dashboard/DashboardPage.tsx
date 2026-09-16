import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useQueries, useQuery } from "@tanstack/react-query";
import { getScan, listScans } from "../../api/scans";
import type { Finding, Severity } from "../../api/types";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import AnomalyBadge from "../../components/ui/AnomalyBadge";
import SeverityBadge from "../../pages/SeverityBadge";

const TOP_RISKS_LIMIT = 5;

// Hex values mirror Member 1's `Badge` Tailwind classes (bg-gray-500 /
// yellow-500 / orange-500 / red-600) so charts and severity badges share one
// palette. Recharts needs raw colors, hence the duplication of the token values.
const SEVERITY_COLORS: Record<Severity, string> = {
  Low: "#6b7280",
  Medium: "#eab308",
  High: "#f97316",
  Critical: "#dc2626",
};

const SEVERITY_ORDER: Severity[] = ["Critical", "High", "Medium", "Low"];

export default function DashboardPage() {
  // Charts are derived from the existing endpoints — no new backend call.
  const scansQuery = useQuery({ queryKey: ["scans"], queryFn: listScans });
  const scans = useMemo(() => scansQuery.data ?? [], [scansQuery.data]);

  // One detail query per scan; keys match ScanDetailPage so the cache is shared.
  const detailQueries = useQueries({
    queries: scans.map((scan) => ({
      queryKey: ["scan", scan.scan_id],
      queryFn: () => getScan(scan.scan_id),
    })),
  });

  const findings: Finding[] = detailQueries.flatMap((q) => q.data?.findings ?? []);

  // Same order as `scans`/`detailQueries`, so each finding can be traced back
  // to the scan it came from (needed for the Top Risks panel's "View scan" link).
  const findingsWithScan = useMemo(
    () =>
      detailQueries.flatMap((q, i) =>
        (q.data?.findings ?? []).map((finding) => ({
          finding,
          scanId: scans[i]?.scan_id,
        })),
      ),
    [detailQueries, scans],
  );

  const topRisks = useMemo(
    () =>
      findingsWithScan
        .filter((f) => f.finding.risk_score != null)
        .sort((a, b) => (b.finding.risk_score ?? 0) - (a.finding.risk_score ?? 0))
        .slice(0, TOP_RISKS_LIMIT),
    [findingsWithScan],
  );

  const severityData = useMemo(() => {
    const counts: Record<Severity, number> = {
      Critical: 0,
      High: 0,
      Medium: 0,
      Low: 0,
    };
    for (const finding of findings) counts[finding.severity] += 1;
    return SEVERITY_ORDER.map((severity) => ({
      name: severity,
      count: counts[severity],
    }));
  }, [findings]);

  const resourceData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const finding of findings) {
      counts[finding.resource_type] = (counts[finding.resource_type] ?? 0) + 1;
    }
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [findings]);

  if (scansQuery.isLoading) {
    return (
      <Card>
        <Spinner />
      </Card>
    );
  }

  if (scansQuery.isError) {
    // Capture to a local so the `typeof` check narrows the value, not the query
    // object (narrowing `scansQuery.error` to a string collapses the union to
    // `never`). The Axios client rejects with a plain string.
    const queryError = scansQuery.error;
    const message =
      typeof queryError === "string" ? queryError : "Failed to load dashboard.";
    return (
      <Card>
        <p className="text-red-700">{message}</p>
      </Card>
    );
  }

  if (scans.length === 0) {
    return (
      <Card>
        <p className="text-sm text-gray-500">
          Nothing to show yet — upload a config to see charts.
        </p>
      </Card>
    );
  }

  if (detailQueries.some((q) => q.isLoading)) {
    return (
      <Card>
        <Spinner />
      </Card>
    );
  }

  const totalFindings = findings.length;

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-gray-500">
          {totalFindings} finding{totalFindings === 1 ? "" : "s"} across {scans.length} scan
          {scans.length === 1 ? "" : "s"}.
        </p>
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Top risks</h2>
        {topRisks.length === 0 ? (
          <p className="text-sm text-gray-500">
            No scored findings yet — risk scoring populates once a scan runs.
          </p>
        ) : (
          <ul className="divide-y">
            {topRisks.map(({ finding, scanId }) => (
              <li
                key={`${scanId}-${finding.resource_id}-${finding.rule_id}`}
                className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs">{finding.resource_id}</p>
                  <p className="text-gray-500">{finding.resource_type}</p>
                </div>
                <div className="flex items-center gap-3">
                  <SeverityBadge severity={finding.severity} />
                  <AnomalyBadge isAnomaly={finding.is_anomaly} />
                  <span className="font-semibold">{finding.risk_score}</span>
                  {scanId && (
                    <Link to={`/scans/${scanId}`} className="text-blue-600 hover:underline">
                      View scan
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Findings by severity</h2>
        {totalFindings === 0 ? (
          <p className="text-sm text-gray-500">No findings to chart yet.</p>
        ) : (
          <>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={severityData} dataKey="count" nameKey="name" outerRadius={90} label>
                    {severityData.map((entry) => (
                      <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name as Severity]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            {/* Text summary: screen-reader friendly and the stable target for tests. */}
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
              {severityData.map((d) => (
                <li key={d.name}>
                  {d.name}: {d.count}
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Findings by resource type</h2>
        {resourceData.length === 0 ? (
          <p className="text-sm text-gray-500">No findings to chart yet.</p>
        ) : (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={resourceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  );
}
