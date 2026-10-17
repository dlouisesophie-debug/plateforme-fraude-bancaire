export default function Pagination({ page, pageSize, count, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3">
      <span className="text-sm text-ink-secondary">
        Page {page} / {totalPages} — {count} résultat{count === 1 ? "" : "s"}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded-xl border border-line px-3 py-1.5 text-sm font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40"
        >
          Précédent
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="rounded-xl border border-line px-3 py-1.5 text-sm font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40"
        >
          Suivant
        </button>
      </div>
    </div>
  );
}
