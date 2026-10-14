export default function StatTile({ label, value }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-6 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-secondary">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink-primary">{value}</p>
    </div>
  );
}
