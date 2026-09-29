import type { ComplianceControl } from "../../api/types";

interface Props {
  controls: ComplianceControl[];
  onSelectControl: (control: ComplianceControl) => void;
}

export default function ControlTable({
  controls,
  onSelectControl,
}: Props) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow">
      <h3 className="mb-4 text-lg font-semibold">Controls</h3>

      {controls.length === 0 ? (
        <p className="text-sm text-gray-500">
          No compliance controls found for this scan.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 font-semibold">Framework</th>
                <th className="px-3 py-2 font-semibold">Control</th>
                <th className="px-3 py-2 font-semibold">Title</th>
                <th className="px-3 py-2 font-semibold">Status</th>
              </tr>
            </thead>

            <tbody>
              {controls.map((control) => (
                <tr
                  key={`${control.framework}-${control.control_id}-${control.rule_id}`}
                  onClick={() => onSelectControl(control)}
                  className="cursor-pointer border-b last:border-b-0 hover:bg-gray-50"
                >
                  <td className="px-3 py-3">{control.framework}</td>
                  <td className="px-3 py-3 font-medium">
                    {control.control_id}
                  </td>
                  <td className="px-3 py-3">{control.title}</td>
                  <td className="px-3 py-3">
                    <span
                      className={
                        control.status === "PASS"
                          ? "rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700"
                          : "rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700"
                      }
                    >
                      {control.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}