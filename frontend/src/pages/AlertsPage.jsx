import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import ScoreBadge from "../components/ScoreBadge";
import Pagination from "../components/Pagination";
import Notice from "../components/Notice";
import { ALERT_STATUS_CHOICES, CHANNEL_CHOICES, SEVERITY_CHOICES, labelFor } from "../constants/choices";
import { INPUT_CLASS, SELECT_CLASS } from "../constants/ui";
import { apiErrorMessage, formatAmount, formatDateTime } from "../utils/format";

const PAGE_SIZE = 20;

function AlertItem({ alert, onUpdated, onError }) {
  const [comment, setComment] = useState(alert.comment || "");
  const [busy, setBusy] = useState(null);
  const [saved, setSaved] = useState(false);
  const dirty = comment !== (alert.comment || "");
  // Clé primaire de la transaction pour le lien vers sa fiche, si l'API la fournit.
  const transactionPk = alert.transaction_pk ?? (typeof alert.transaction === "number" ? alert.transaction : null);

  async function run(kind, request) {
    setBusy(kind);
    setSaved(false);
    onError(null);
    try {
      const { data } = await request();
      onUpdated({ ...alert, ...data });
      if (kind === "comment") setSaved(true);
    } catch (err) {
      onError(apiErrorMessage(err, "Action impossible sur cette alerte."));
    } finally {
      setBusy(null);
    }
  }

  const decide = (action) => run(action, () => api.post(`/alerts/${alert.id}/${action}/`, { comment }));
  const saveComment = () => run("comment", () => api.patch(`/alerts/${alert.id}/`, { comment }));

  return (
    <li className="px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-ink-primary">Alerte #{alert.id}</span>
            <StatusBadge value={alert.status} label={labelFor(ALERT_STATUS_CHOICES, alert.status)} />
            <StatusBadge value={alert.severity} label={`Sévérité : ${labelFor(SEVERITY_CHOICES, alert.severity)}`} />
          </div>
          <p className="mt-1 text-sm text-ink-secondary">
            {transactionPk ? (
              <Link to={`/transactions/${transactionPk}`} className="font-medium text-brand hover:underline">
                {alert.transaction_id ?? `Transaction #${transactionPk}`}
              </Link>
            ) : (
              <span className="font-medium text-ink-primary">{alert.transaction_id ?? "—"}</span>
            )}
            {" · "}
            <span className="tabular-nums">{formatAmount(alert.amount)}</span>
            {" · "}
            {labelFor(CHANNEL_CHOICES, alert.channel) ?? "—"}
            {" · "}
            {formatDateTime(alert.timestamp ?? alert.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          Score <ScoreBadge value={alert.fraud_probability} />
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-start">
        <label htmlFor={`comment-${alert.id}`} className="sr-only">
          Commentaire de l'alerte #{alert.id}
        </label>
        <textarea
          id={`comment-${alert.id}`}
          rows={2}
          value={comment}
          onChange={(e) => {
            setComment(e.target.value);
            setSaved(false);
          }}
          placeholder="Commentaire de l'analyste..."
          className={`${INPUT_CLASS} sm:flex-1`}
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!dirty || busy !== null}
            onClick={saveComment}
            className="rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === "comment" ? "Enregistrement..." : saved ? "Enregistré ✓" : "Annoter"}
          </button>
          {alert.status === "open" && (
            <>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => decide("confirm")}
                className="rounded-xl bg-danger px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Confirmer la fraude
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => decide("reject")}
                className="rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50"
              >
                Rejeter
              </button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  function handleUpdated(updated) {
    setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  }

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Alertes</h1>

      <div className="mt-6 flex flex-wrap gap-3">
        <select value={status} onChange={handleFilterChange(setStatus)} aria-label="Statut" className={SELECT_CLASS}>
          <option value="">Tous les statuts</option>
          {ALERT_STATUS_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select value={severity} onChange={handleFilterChange(setSeverity)} aria-label="Sévérité" className={SELECT_CLASS}>
          <option value="">Toutes les sévérités</option>
          {SEVERITY_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <Notice className="mt-4">{error}</Notice>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <ul className="divide-y divide-line">
          {!loading &&
            alerts.map((a) => <AlertItem key={a.id} alert={a} onUpdated={handleUpdated} onError={setError} />)}
          {!loading && alerts.length === 0 && !error && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">Aucune alerte</li>
          )}
          {loading && <li className="px-4 py-6 text-center text-sm text-ink-secondary">Chargement...</li>}
        </ul>
        {!loading && count > 0 && (
          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />
        )}
      </div>
    </Layout>
  );
}
