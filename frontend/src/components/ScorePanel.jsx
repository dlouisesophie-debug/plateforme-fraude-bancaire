import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import { scoreTone } from "./ScoreBadge";
import { ALERT_STATUS_CHOICES, TRANSACTION_STATUS_CHOICES, labelFor } from "../constants/choices";
import { formatProbability, formatVersion } from "../utils/format";
import { scoringInfo } from "../utils/transaction";

// Bloc "verdict du modèle" : score, statut, version du modèle, alerte liée.
export default function ScorePanel({ transaction, showAlertLink = false }) {
  const { probability, modelVersion, isFraud, alertId, alertStatus } = scoringInfo(transaction);
  const scored = probability !== null && probability !== undefined;
  // Même règle que ScoreBadge : la couleur suit la prédiction du modèle.
  const barColor = isFraud === true ? "bg-danger" : isFraud === false ? "bg-success" : "bg-ink-secondary";

  return (
    <div className="rounded-xl border border-line bg-surface p-6 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-secondary">Score de fraude</p>
      {scored ? (
        <>
          <p className={`mt-3 inline-flex rounded-xl px-4 py-2 text-4xl font-semibold tabular-nums ${scoreTone(isFraud)}`}>
            {formatProbability(probability)}
          </p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-canvas">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${Math.min(100, Math.max(2, Number(probability) * 100))}%` }}
            />
          </div>
        </>
      ) : (
        <p className="mt-3 text-sm text-ink-secondary">
          Transaction non scorée (aucun modèle actif ou scoring en échec).
        </p>
      )}

      <dl className="mt-5 space-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <dt className="text-ink-secondary">Statut</dt>
          <dd>
            <StatusBadge value={transaction.status} label={labelFor(TRANSACTION_STATUS_CHOICES, transaction.status)} />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-ink-secondary">Modèle</dt>
          <dd className="font-medium text-ink-primary">{formatVersion(modelVersion)}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-ink-secondary">Alerte liée</dt>
          <dd className="flex items-center gap-2">
            {alertId ? (
              <>
                <span className="font-medium text-ink-primary">#{alertId}</span>
                <StatusBadge value={alertStatus} label={labelFor(ALERT_STATUS_CHOICES, alertStatus)} />
              </>
            ) : (
              <span className="text-ink-secondary">Aucune</span>
            )}
          </dd>
        </div>
      </dl>

      {showAlertLink && alertId && (
        <Link to={`/alerts?id=${alertId}`} className="mt-4 inline-block text-sm font-medium text-brand hover:underline">
          Traiter l'alerte →
        </Link>
      )}
    </div>
  );
}
