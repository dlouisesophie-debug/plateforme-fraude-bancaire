import { useEffect, useState } from "react";
import api from "../services/api";
import Layout from "../components/Layout";
import StatTile from "../components/StatTile";
import StatusBadge from "../components/StatusBadge";
import Notice from "../components/Notice";
import { ALGORITHM_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS } from "../constants/ui";
import { asList, formatDateTime, formatProbability } from "../utils/format";

const METRICS = [
  ["precision_score", "Précision"],
  ["recall_score", "Rappel"],
  ["f1_score", "F1-score"],
  ["auc_roc", "AUC-ROC"],
];

export default function ModelPage() {
  const [activeModel, setActiveModel] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([api.get("/dashboard/stats/"), api.get("/fraud-detection/models/")])
      .then(([statsRes, modelsRes]) => {
        if (cancelled) return;
        const list = modelsRes.status === "fulfilled" ? asList(modelsRes.value.data) : [];
        setModels(list);
        const fromStats = statsRes.status === "fulfilled" ? statsRes.value.data.active_model : null;
        setActiveModel(fromStats || list.find((m) => m.is_active) || null);
        if (modelsRes.status === "rejected" && statsRes.status === "rejected") {
          setError("Impossible de charger les informations du modèle.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Modèle IA</h1>

      <Notice className="mt-6">{error}</Notice>
      {loading && <p className="mt-6 text-sm text-ink-secondary">Chargement...</p>}

      {!loading && !error && (
        <>
          <section className={`${CARD_CLASS} mt-6`}>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-secondary">Modèle actif</p>
            {activeModel ? (
              <>
                <p className="mt-2 font-display text-2xl font-semibold text-ink-primary">
                  {labelFor(ALGORITHM_CHOICES, activeModel.algorithm)} v{activeModel.version}
                </p>
                <p className="mt-1 text-sm text-ink-secondary">Entraîné le {formatDateTime(activeModel.trained_at)}</p>
              </>
            ) : (
              <p className="mt-2 text-sm text-ink-secondary">
                Aucun modèle actif : les transactions ne sont pas scorées (commande « activer_modele_ml »).
              </p>
            )}
          </section>

          {activeModel && (
            <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
              {METRICS.map(([key, label]) => (
                <StatTile key={key} label={label} value={formatProbability(activeModel[key])} />
              ))}
            </div>
          )}

          <h2 className="mt-8 text-sm font-medium text-ink-primary">Historique des modèles</h2>
          <div className="mt-3 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-canvas text-xs font-medium uppercase tracking-wide text-ink-secondary">
                  <tr>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Algorithme</th>
                    {METRICS.map(([key, label]) => (
                      <th key={key} className="px-4 py-3 text-right">
                        {label}
                      </th>
                    ))}
                    <th className="px-4 py-3">Entraîné le</th>
                    <th className="px-4 py-3">État</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {models.map((m) => (
                    <tr key={m.id} className="text-ink-primary">
                      <td className="whitespace-nowrap px-4 py-3 font-medium">v{m.version}</td>
                      <td className="whitespace-nowrap px-4 py-3">{labelFor(ALGORITHM_CHOICES, m.algorithm)}</td>
                      {METRICS.map(([key]) => (
                        <td key={key} className="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                          {formatProbability(m[key])}
                        </td>
                      ))}
                      <td className="whitespace-nowrap px-4 py-3 text-ink-secondary">{formatDateTime(m.trained_at)}</td>
                      <td className="px-4 py-3">
                        <StatusBadge value={m.is_active ? "legitimate" : "pending"} label={m.is_active ? "Actif" : "Inactif"} />
                      </td>
                    </tr>
                  ))}
                  {models.length === 0 && (
                    <tr>
                      <td colSpan={METRICS.length + 4} className="px-4 py-6 text-center text-ink-secondary">
                        Aucun modèle enregistré
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
