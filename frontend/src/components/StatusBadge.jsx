const TONES = {
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  neutral: "bg-brand-soft text-brand",
};

const TONE_BY_VALUE = {
  legitimate: "success",
  confirmed: "success",
  resolved: "success",
  low: "success",
  pending: "warning",
  open: "warning",
  medium: "warning",
  under_review: "neutral",
  fraudulent: "danger",
  rejected: "danger",
  high: "danger",
  critical: "danger",
};

export default function StatusBadge({ value, label }) {
  const key = String(value ?? "").toLowerCase();
  const tone = TONES[TONE_BY_VALUE[key]] ?? TONES.neutral;

  return (
    <span className={`inline-flex items-center rounded-xl px-2.5 py-1 text-xs font-medium ${tone}`}>
      {label ?? value ?? "—"}
    </span>
  );
}
