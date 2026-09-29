import type {
  ComplianceFramework,
  ComplianceStatus,
} from "../../api/types";

interface Props {
  framework: ComplianceFramework | "ALL";
  status: ComplianceStatus | "ALL";
  onFrameworkChange: (
    framework: ComplianceFramework | "ALL",
  ) => void;
  onStatusChange: (status: ComplianceStatus | "ALL") => void;
}

export default function ComplianceFilters({
  framework,
  status,
  onFrameworkChange,
  onStatusChange,
}: Props) {
  return (
    <div className="flex flex-wrap gap-4 rounded-lg border bg-white p-4 shadow">
      <label className="flex items-center gap-2 text-sm font-medium">
        Framework:
        <select
          value={framework}
          onChange={(event) =>
            onFrameworkChange(
              event.target.value as ComplianceFramework | "ALL",
            )
          }
          className="rounded border px-3 py-2 text-sm font-normal"
        >
          <option value="ALL">All</option>
          <option value="CIS">CIS</option>
          <option value="NIST">NIST</option>
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm font-medium">
        Status:
        <select
          value={status}
          onChange={(event) =>
            onStatusChange(
              event.target.value as ComplianceStatus | "ALL",
            )
          }
          className="rounded border px-3 py-2 text-sm font-normal"
        >
          <option value="ALL">All</option>
          <option value="PASS">Pass</option>
          <option value="FAIL">Fail</option>
        </select>
      </label>
    </div>
  );
}