import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getScanCompliance } from "../../api/scans";
import type {
  ComplianceControl,
  ComplianceFramework,
  ComplianceStatus,
} from "../../api/types";

import FrameworkSummary from "./FrameworkSummary";
import ControlTable from "./ControlTable";
import RemediationPanel from "./RemediationPanel";
import ComplianceFilters from "./ComplianceFilters";

interface Props {
  scanId: string;
}

export default function CompliancePage({ scanId }: Props) {
  const [framework, setFramework] =
    useState<ComplianceFramework | "ALL">("ALL");

  const [status, setStatus] =
    useState<ComplianceStatus | "ALL">("ALL");

  const [selectedControl, setSelectedControl] =
    useState<ComplianceControl | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["scan-compliance", scanId],
    queryFn: () => getScanCompliance(scanId),
    enabled: Boolean(scanId),
  });

  const filteredControls = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.controls.filter((control) => {
      const frameworkMatches =
        framework === "ALL" || control.framework === framework;

      const statusMatches =
        status === "ALL" || control.status === status;

      return frameworkMatches && statusMatches;
    });
  }, [data, framework, status]);

  if (isLoading) {
    return <p>Loading compliance...</p>;
  }

  if (isError || !data) {
    return <p>Unable to load compliance data.</p>;
  }

  return (
   <div className="space-y-4">
    <h2 className="text-xl font-semibold">Compliance</h2>

    <div className="grid gap-4 md:grid-cols-2">
      {Object.entries(data.frameworks).map(
        ([frameworkName, summary]) => (
          <FrameworkSummary
            key={frameworkName}
            framework={frameworkName}
            summary={summary}
          />
        ),
      )}
    </div>

    <ComplianceFilters
      framework={framework}
      status={status}
      onFrameworkChange={setFramework}
      onStatusChange={setStatus}
    />

    <ControlTable
      controls={filteredControls}
      onSelectControl={setSelectedControl}
    />

    <RemediationPanel control={selectedControl} />
  </div>
);
}