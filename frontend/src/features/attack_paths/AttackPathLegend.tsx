/**
 * Member 4 — AttackPathLegend
 *
 * Two keys: node color (severity -- the same encoding Badge already teaches
 * on every other page) and link meaning (relationship vocabulary from
 * Member 3's Contract 2). The relationship key exists because the same
 * dashed-vs-solid-style question the diagramming guidance raises for any
 * repeated encoding applies here too: an arrow labeled "ASSUMES" only means
 * something once, so it belongs in a legend, not restated on every edge.
 */

const SEVERITY_ITEMS: { label: string; swatchClass: string }[] = [
  { label: "Critical", swatchClass: "bg-red-600" },
  { label: "High", swatchClass: "bg-orange-500" },
  { label: "Medium", swatchClass: "bg-yellow-500" },
  { label: "Low", swatchClass: "bg-gray-500" },
];

const RELATIONSHIP_ITEMS: { relationship: string; meaning: string }[] = [
  { relationship: "EXPOSES", meaning: "internet-reachable ingress" },
  { relationship: "ASSUMES", meaning: "compute assumes an IAM role" },
  { relationship: "HAS_PERMISSION", meaning: "role is granted a policy" },
  { relationship: "ACCESSES", meaning: "policy grants access to a data store" },
];

export default function AttackPathLegend() {
  return (
    <div className="flex flex-col gap-2 text-xs text-gray-600">
      <div className="flex flex-wrap items-center gap-3">
        {SEVERITY_ITEMS.map((item) => (
          <span key={item.label} className="flex items-center gap-1">
            <span className={`h-2.5 w-2.5 rounded-full ${item.swatchClass}`} />
            {item.label}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {RELATIONSHIP_ITEMS.map((item) => (
          <span key={item.relationship}>
            <span className="font-mono font-medium text-gray-500">{item.relationship}</span>{" "}
            &mdash; {item.meaning}
          </span>
        ))}
      </div>
    </div>
  );
}
