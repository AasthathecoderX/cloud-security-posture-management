import type { FrameworkSummary as FrameworkSummaryType } from "../../api/types";

interface Props {
  framework: string;
  summary: FrameworkSummaryType;
}

export default function FrameworkSummary({ framework, summary }: Props) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow">
      <h3 className="mb-3 text-lg font-semibold">{framework}</h3>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded border p-3">
          <p className="text-sm text-gray-500">Passed</p>
          <p className="text-xl font-semibold text-green-600">
            {summary.passed}
          </p>
        </div>

        <div className="rounded border p-3">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-xl font-semibold text-red-600">
            {summary.failed}
          </p>
        </div>

        <div className="rounded border p-3">
          <p className="text-sm text-gray-500">Total</p>
          <p className="text-xl font-semibold">
            {summary.total}
          </p>
        </div>
      </div>
    </div>
  );
}