import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";
import Layout from "../components/Layout";
import ScorePanel from "../components/ScorePanel";
import Notice from "../components/Notice";
import { useAuth } from "../hooks/useAuth";
import { canAccess } from "../constants/roles";
import { CATEGORY_CHOICES, CHANNEL_CHOICES, TRANSACTION_STATUS_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON, SELECT_CLASS } from "../constants/ui";
import { apiErrorMessage, formatAmount, formatDate, formatDateTime, formatNumber } from "../utils/format";
import { TRANSACTION_FIELD_GROUPS } from "../utils/transaction";

const REQUALIFY_ROLES = ["admin", "analyst"];

// EF-13 : un admin/analyste peut changer le statut d'une transaction. L'API
// reclasse elle-même l'alerte liée (confirmed/rejected) si elle était ouverte.
function Requalify({ transaction, onUpdated }) {
  const options = TRANSACTION_STATUS_CHOICES.filter((c) => c.value !== transaction.status);
  const [newStatus, setNewStatus] = useState(options[0]?.value ?? "");
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleConfirm() {
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/transactions/${transaction.id}/`, { status: newStatus });
      await onUpdated();
      setConfirming(false);
    } catch (err) {
      setError(apiErrorMessage(err, "Requalification impossible."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className={`${CARD_CLASS} mt-4`}>
      <h2 className="text-sm font-medium text-ink-primary">Requalifier</h2>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select
          value={newStatus}
          onChange={(e) => {
            setNewStatus(e.target.value);
            setConfirming(false);
          }}
          disabled={saving}
          aria-label="Nouveau statut"
          className={SELECT_CLASS}
        >
          {options.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        {confirming ? (
          <>
            <button type="button" onClick={handleConfirm} disabled={saving} className={PRIMARY_BUTTON}>
              {saving ? "Enregistrement..." : "Confirmer"}
            </button>
            <button type="button" onClick={() => setConfirming(false)} disabled={saving} className={SECONDARY_BUTTON}>
              Annuler
            </button>
          </>
        ) : (
          <button type="button" onClick={() => setConfirming(true)} className={SECONDARY_BUTTON}>
            Requalifier
          </button>
        )}
      </div>
      <Notice className="mt-3">{error}</Notice>
    </section>
  );
}

function formatField(key, value, transaction) {
  if (value === null || value === undefined || value === "") return "—";
  switch (key) {
    case "amount":
      return formatAmount(value);
    case "channel":
      return labelFor(CHANNEL_CHOICES, value);
    case "category":
      return labelFor(CATEGORY_CHOICES, value);
    case "timestamp":
    case "created_at":
      return formatDateTime(value);
    case "customer_birth_date":
      return formatDate(value);
    case "customer_city_population":
      return formatNumber(value);
    case "created_by":
      return transaction.created_by_username || `Utilisateur #${value}`;
    default:
      return String(value);
  }
}

export default function TransactionDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [transaction, setTransaction] = useState(null);
  const [error, setError] = useState(null);

  function reload() {
    return api.get(`/transactions/${id}/`).then((res) => setTransaction(res.data));
  }

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setTransaction(null);
    api
      .get(`/transactions/${id}/`)
      .then((res) => {
        if (!cancelled) setTransaction(res.data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.response?.status === 404 ? "Transaction introuvable." : "Impossible de charger la transaction.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <Layout>
      <Link to="/transactions" className="text-sm font-medium text-brand hover:underline">
        ← Retour aux transactions
      </Link>

      <Notice className="mt-4">{error}</Notice>
      {!error && !transaction && <p className="mt-6 text-sm text-ink-secondary">Chargement...</p>}

      {transaction && (
        <>
          <h1 className="mt-3 font-display text-2xl font-semibold text-ink-primary">
            Transaction {transaction.transaction_id}
          </h1>
          <p className="mt-1 text-sm text-ink-secondary">
            {formatAmount(transaction.amount)} · {labelFor(CHANNEL_CHOICES, transaction.channel)} ·{" "}
            {formatDateTime(transaction.timestamp)}
          </p>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-1">
              <ScorePanel transaction={transaction} showAlertLink={canAccess(user, REQUALIFY_ROLES)} />
              {canAccess(user, REQUALIFY_ROLES) && <Requalify transaction={transaction} onUpdated={reload} />}
            </div>
            <div className="space-y-4 lg:col-span-2">
              {TRANSACTION_FIELD_GROUPS.map((group) => (
                <section key={group.title} className={CARD_CLASS}>
                  <h2 className="text-sm font-medium text-ink-primary">{group.title}</h2>
                  <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                    {group.fields.map(([key, label]) => (
                      <div key={key} className="flex justify-between gap-3 border-b border-line pb-2 sm:block sm:border-0 sm:pb-0">
                        <dt className="text-ink-secondary">{label}</dt>
                        <dd className="break-words text-right font-medium text-ink-primary sm:mt-0.5 sm:text-left">
                          {formatField(key, transaction[key], transaction)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))}
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
