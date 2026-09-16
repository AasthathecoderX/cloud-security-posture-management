type AnomalyBadgeProps = {
  isAnomaly: boolean;
};

// Purple, deliberately distinct from Badge's severity palette (gray/yellow/
// orange/red): severity is a rule verdict, anomaly is a separate statistical
// signal (Isolation Forest, per the ML strategy in Major Project Planning.md
// §8.2) that can fire independently of severity, so it gets its own color.
export default function AnomalyBadge({ isAnomaly }: AnomalyBadgeProps) {
  if (!isAnomaly) {
    return <span className="text-sm text-gray-400">No</span>;
  }
  return (
    <span className="px-2 py-1 rounded text-white text-sm bg-purple-600">
      Anomaly
    </span>
  );
}
