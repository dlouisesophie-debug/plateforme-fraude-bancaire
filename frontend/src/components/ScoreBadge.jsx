import { formatProbability } from "../utils/format";

// Score de fraude (fraud_probability 0..1) affiché en pourcentage coloré.
export function scoreTone(probability) {
  if (probability >= 0.5) return "bg-danger-soft text-danger";
  if (probability >= 0.1) return "bg-warning-soft text-warning";
  return "bg-success-soft text-success";
}

export default function ScoreBadge({ value }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-secondary">—</span>;
  }
  return (
    <span className={`inline-flex items-center rounded-xl px-2.5 py-1 text-xs font-semibold tabular-nums ${scoreTone(Number(value))}`}>
      {formatProbability(value)}
    </span>
  );
}
