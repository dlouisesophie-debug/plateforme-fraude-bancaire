import { useEffect, useState } from "react";
import api from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import Pagination from "../components/Pagination";
import { CHANNEL_CHOICES, TRANSACTION_STATUS_CHOICES, labelFor } from "../constants/choices";

const PAGE_SIZE = 20;

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get("/transactions/", { params: { page, status: status || undefined, channel: channel || undefined } })
      .then((res) => {
        if (cancelled) return;
        setTransactions(res.data.results || []);
        setCount(res.data.count || 0);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger les transactions.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, status, channel]);

  function handleFilterChange(setter) {
    return (e) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Transactions</h1>

      <div className="mt-6 flex flex-wrap gap-3">
        <select
          value={status}
          onChange={handleFilterChange(setStatus)}
          className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink-primary outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          <option value="">Tous les statuts</option>
          {TRANSACTION_STATUS_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          value={channel}
          onChange={handleFilterChange(setChannel)}
          className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink-primary outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          <option value="">Tous les canaux</option>
          {CHANNEL_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>
      )}

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas text-xs font-medium uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Montant</th>
                <th className="px-4 py-3">Canal</th>
                <th className="px-4 py-3">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {!loading &&
                transactions.map((t) => (
                  <tr key={t.id} className="text-ink-primary">
                    <td className="px-4 py-3">{t.transaction_id}</td>
                    <td className="px-4 py-3">{t.amount}</td>
                    <td className="px-4 py-3">{labelFor(CHANNEL_CHOICES, t.channel)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge value={t.status} label={labelFor(TRANSACTION_STATUS_CHOICES, t.status)} />
                    </td>
                  </tr>
                ))}
              {!loading && transactions.length === 0 && !error && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-ink-secondary">
                    Aucune transaction
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-ink-secondary">
                    Chargement...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {!loading && count > 0 && (
          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />
        )}
      </div>
    </Layout>
  );
}
