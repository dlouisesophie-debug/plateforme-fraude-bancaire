import { useEffect, useState } from "react";
import api from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import Pagination from "../components/Pagination";
import { ALERT_STATUS_CHOICES, SEVERITY_CHOICES, labelFor } from "../constants/choices";

const PAGE_SIZE = 20;

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actioningId, setActioningId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get("/alerts/", { params: { page, status: status || undefined, severity: severity || undefined } })
      .then((res) => {
        if (cancelled) return;
        setAlerts(res.data.results || []);
        setCount(res.data.count || 0);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger les alertes.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, status, severity]);

  function handleFilterChange(setter) {
    return (e) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  async function handleAction(alertId, action) {
    setActioningId(alertId);
    setError(null);
    try {
      const { data } = await api.post(`/alerts/${alertId}/${action}/`);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? data : a)));
    } catch (err) {
      setError("Action impossible sur cette alerte.");
    } finally {
      setActioningId(null);
    }
  }

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Alertes</h1>

      <div className="mt-6 flex flex-wrap gap-3">
        <select
          value={status}
          onChange={handleFilterChange(setStatus)}
          className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink-primary outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          <option value="">Tous les statuts</option>
          {ALERT_STATUS_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          value={severity}
          onChange={handleFilterChange(setSeverity)}
          className="rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink-primary outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          <option value="">Toutes les severites</option>
          {SEVERITY_CHOICES.map((c) => (
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
        <ul className="divide-y divide-line">
          {!loading &&
            alerts.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-ink-primary">
                    Alerte #{a.id} — {labelFor(SEVERITY_CHOICES, a.severity)}
                  </span>
                  <StatusBadge value={a.status} label={labelFor(ALERT_STATUS_CHOICES, a.status)} />
                </div>
                {a.status === "open" && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={actioningId === a.id}
                      onClick={() => handleAction(a.id, "confirm")}
                      className="rounded-xl bg-danger px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Confirmer
                    </button>
                    <button
                      type="button"
                      disabled={actioningId === a.id}
                      onClick={() => handleAction(a.id, "reject")}
                      className="rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Rejeter
                    </button>
                  </div>
                )}
              </li>
            ))}
          {!loading && alerts.length === 0 && !error && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">Aucune alerte</li>
          )}
          {loading && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">Chargement...</li>
          )}
        </ul>
        {!loading && count > 0 && (
          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />
        )}
      </div>
    </Layout>
  );
}
