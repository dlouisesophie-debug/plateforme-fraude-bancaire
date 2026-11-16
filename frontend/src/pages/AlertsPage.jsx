import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import ScoreBadge from "../components/ScoreBadge";
import Pagination from "../components/Pagination";
import Notice from "../components/Notice";
import { ALERT_STATUS_CHOICES, CHANNEL_CHOICES, SEVERITY_CHOICES, labelFor } from "../constants/choices";
import { INPUT_CLASS, SELECT_CLASS } from "../constants/ui";
import { apiErrorMessage, formatDateTime, formatDuration, formatTransactionAmount } from "../utils/format";

const PAGE_SIZE = 20;

// Heure courante rafraîchie régulièrement, pour que « suspendu depuis » avance à l'écran.
function useNow(intervalMs) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}

// Conséquence sur le paiement (suspension temporaire) : alerte ouverte = paiement suspendu ;
// fraude confirmée = paiement refusé ; alerte rejetée = paiement libéré. Les durées viennent
// des dates de l'alerte (created_at = début de la suspension, resolved_at = décision).
const DECIDED_PAYMENT = { confirmed: "Paiement refusé", rejected: "Paiement libéré" };

function PaymentLine({ alert, now }) {
  let state;
  let detail = null;
  if (alert.status === "open") {
    state = "Paiement suspendu";
    const since = formatDuration(alert.created_at, now);
    if (since) detail = ` depuis ${since}`;
  } else if (DECIDED_PAYMENT[alert.status]) {
    state = DECIDED_PAYMENT[alert.status];
    const delay = formatDuration(alert.created_at, alert.resolved_at);
    if (delay) detail = ` · vérifié en ${delay}`;
  } else {
    return null;
  }
  return (
    <p className="mt-1 text-sm">
      <span className="font-medium text-ink-primary">{state}</span>
      {detail && <span className="text-ink-secondary">{detail}</span>}
    </p>
  );
}

function AlertItem({ alert, now, onUpdated, onError }) {
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
            <span className="tabular-nums">{formatTransactionAmount(alert)}</span>
            {" · "}
            {labelFor(CHANNEL_CHOICES, alert.channel) ?? "—"}
            {" · "}
            {formatDateTime(alert.timestamp ?? alert.created_at)}
          </p>
          <PaymentLine alert={alert} now={now} />
        </div>
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          {/* Une alerte n'est créée que si le modèle a prédit une fraude. */}
          Score <ScoreBadge value={alert.fraud_probability} isFraud />
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
                Confirmer la fraude (paiement refusé)
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => decide("reject")}
                className="rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50"
              >
                Rejeter (libérer le paiement)
              </button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

export default function AlertsPage() {
  // ?id=12 : ouvre directement une alerte (lien « Traiter l'alerte » de la fiche transaction).
  const [searchParams] = useSearchParams();
  const focusId = searchParams.get("id");
  const [alerts, setAlerts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const now = useNow(30000);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const request = focusId
      ? api.get(`/alerts/${focusId}/`).then((res) => ({ results: [res.data], count: 1 }))
      : api
          .get("/alerts/", { params: { page, status: status || undefined, severity: severity || undefined } })
          .then((res) => res.data);

    request
      .then((data) => {
        if (cancelled) return;
        setAlerts(data.results || []);
        setCount(data.count || 0);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(focusId && err.response?.status === 404 ? `Alerte #${focusId} introuvable.` : "Impossible de charger les alertes.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [focusId, page, status, severity]);

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
      {focusId && (
        <Link to="/alerts" className="text-sm font-medium text-brand hover:underline">
          ← Toutes les alertes
        </Link>
      )}
      <h1 className={`font-display text-2xl font-semibold text-ink-primary ${focusId ? "mt-3" : ""}`}>
        {focusId ? `Alerte #${focusId}` : "Alertes"}
      </h1>

      {!focusId && (
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
      )}

      <Notice className="mt-4">{error}</Notice>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <ul className="divide-y divide-line">
          {!loading &&
            alerts.map((a) => (
              <AlertItem key={a.id} alert={a} now={now} onUpdated={handleUpdated} onError={setError} />
            ))}
          {!loading && alerts.length === 0 && !error && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">Aucune alerte</li>
          )}
          {loading && <li className="px-4 py-6 text-center text-sm text-ink-secondary">Chargement...</li>}
        </ul>
        {!loading && !focusId && count > 0 && (
          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />
        )}
      </div>
    </Layout>
  );
}
