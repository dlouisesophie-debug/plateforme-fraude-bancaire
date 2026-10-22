import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";
import Layout from "../components/Layout";
import ScorePanel from "../components/ScorePanel";
import Notice from "../components/Notice";
import { useAuth } from "../hooks/useAuth";
import { canAccess } from "../constants/roles";
import { CATEGORY_CHOICES, CHANNEL_CHOICES, GENDER_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS } from "../constants/ui";
import { formatAmount, formatDate, formatDateTime, formatNumber } from "../utils/format";
import { TRANSACTION_FIELD_GROUPS } from "../utils/transaction";

function formatField(key, value, transaction) {
  if (value === null || value === undefined || value === "") return "—";
  switch (key) {
    case "amount":
      return formatAmount(value);
    case "channel":
      return labelFor(CHANNEL_CHOICES, value);
    case "category":
      return labelFor(CATEGORY_CHOICES, value);
    case "customer_gender":
      return labelFor(GENDER_CHOICES, value);
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
              <ScorePanel transaction={transaction} showAlertLink={canAccess(user, ["admin", "analyst"])} />
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
