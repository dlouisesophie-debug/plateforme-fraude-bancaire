import { formatProbability } from "../utils/format";

// Couleur du score = décision du modèle (fraude / non fraude), pas des seuils
// fixes : le seuil de décision dépend du modèle actif (0,0652 pour le modèle
// carte), donc un score de 8 % est une fraude et doit apparaître en rouge.
export function scoreTone(isFraud) {
  if (isFraud === true) return "bg-danger-soft text-danger";
  if (isFraud === false) return "bg-success-soft text-success";
  return "bg-canvas text-ink-secondary"; // décision inconnue
}

// Score de fraude (fraud_probability 0..1) affiché en pourcentage, coloré
// selon la prédiction du modèle (is_fraud_predicted).
export default function ScoreBadge({ value, isFraud }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-secondary">—</span>;
  }
  return (
    <span className={`inline-flex items-center rounded-xl px-2.5 py-1 text-xs font-semibold tabular-nums ${scoreTone(isFraud)}`}>
      {formatProbability(value)}
    </span>
  );
}
