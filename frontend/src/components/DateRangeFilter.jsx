import { SELECT_CLASS } from "../constants/ui";

// Filtre de période envoyé au backend sous la forme ?date_after= & ?date_before=.
export default function DateRangeFilter({ after, before, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-ink-secondary">
      <label className="flex items-center gap-2">
        Du
        <input
          type="date"
          value={after}
          max={before || undefined}
          onChange={(e) => onChange({ after: e.target.value, before })}
          className={SELECT_CLASS}
        />
      </label>
      <label className="flex items-center gap-2">
        au
        <input
          type="date"
          value={before}
          min={after || undefined}
          onChange={(e) => onChange({ after, before: e.target.value })}
          className={SELECT_CLASS}
        />
      </label>
      {(after || before) && (
        <button
          type="button"
          onClick={() => onChange({ after: "", before: "" })}
          className="rounded-xl px-2 py-1 text-sm font-medium text-brand hover:bg-brand-soft"
        >
          Effacer
        </button>
      )}
    </div>
  );
}
