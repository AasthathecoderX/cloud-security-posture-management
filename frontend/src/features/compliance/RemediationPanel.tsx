import type { ComplianceControl } from "../../api/types";

interface Props {
  control: ComplianceControl | null;
}

export default function RemediationPanel({ control }: Props) {
  if (!control) {
    return (
      <div className="rounded-lg border bg-white p-4 shadow">
        <h3 className="mb-2 text-lg font-semibold">Remediation</h3>
        <p className="text-sm text-gray-500">
          Select a control to view remediation guidance.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white p-4 shadow">
      <h3 className="mb-3 text-lg font-semibold">Remediation</h3>

      <p className="mb-3">
        <strong>{control.control_id}</strong> — {control.title}
      </p>

      <div className="rounded border bg-gray-50 p-3">
        <p className="text-sm leading-6">{control.remediation}</p>
      </div>

      {control.finding_ids.length > 0 && (
        <div className="mt-4">
          <strong className="text-sm">Associated findings:</strong>

          <ul className="mt-2 list-disc pl-5 text-sm text-gray-600">
            {control.finding_ids.map((findingId) => (
              <li key={findingId}>{findingId}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}