import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScan } from "../api/scans";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import FindingsTable from "./FindingsTable";
import { CompliancePage } from "../features/compliance";
import { AttackPathPage } from "../features/attack_paths";

/**
 * Member 3 — ScanDetailPage
 *
 * Reads the :id route param, fetches getScan(id), shows the scan header and
 * a FindingsTable. Handles 404 (scan not found) gracefully.
 */
export default function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<
    "findings" | "attack-paths" | "compliance"
  >("findings");

  const {
    data: scan,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["scan", id],
    queryFn: () => getScan(id as string),
    enabled: Boolean(id),
  });

  if (isLoading) {
    return (
      <Card>
        <Spinner />
      </Card>
    );
  }

  if (isError) {
    const message = typeof error === "string" ? error : "";
    const isNotFound = message.toLowerCase().includes("not found");

    return (
      <Card>
        {isNotFound ? (
          <div>
            <p className="font-medium">Scan not found.</p>
            <p className="mt-1 text-sm text-gray-500">
              It may have been removed, or the link is incorrect.
            </p>
            <Link to="/scans" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
              Back to scans
            </Link>
          </div>
        ) : (
          <p className="text-red-700">{message || "Failed to load scan."}</p>
        )}
      </Card>
    );
  }

  if (!scan) {
    return null;
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{scan.filename}</h2>
            <p className="text-sm text-gray-500">
              {scan.scan_type} · {scan.status} ·{" "}
              {new Date(scan.timestamp).toLocaleString()}
            </p>
          </div>
          <Link to="/scans" className="text-sm text-blue-600 hover:underline">
            Back to scans
          </Link>
        </div>
      </Card>

      <div className="flex gap-4 border-b">
        <button
          type="button"
          onClick={() => setActiveTab("findings")}
          className="pb-2"
        >
          Findings
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("attack-paths")}
          className="pb-2"
        >
          Attack Paths
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("compliance")}
          className="pb-2"
        >
          Compliance
        </button>
      </div>

      {activeTab === "findings" && (
        <Card>
          <FindingsTable findings={scan.findings} />
        </Card>
      )}

      {activeTab === "attack-paths" && <AttackPathPage scanId={id as string} />}

      {activeTab === "compliance" && (
        <CompliancePage scanId={id as string} />
      )}
    </div>
  );
}
