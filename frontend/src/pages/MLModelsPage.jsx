import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const ALGO_LABELS = {
  logistic_regression: "Régression logistique",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

function MetricBar({ label, value }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-ink-secondary">{label}</span>
        <span className="font-semibold">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-line rounded-full overflow-hidden">
        <div className="h-full bg-brand rounded-full" style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}

export default function MLModelsPage() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user] = useState(mockUser);

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG ? await mockApi.getMLModels() : (await api.get("/fraud-detection/models/")).data;
      setModels(data.results || []);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Modèles ML" />

        <div className="p-7">
          <div className="text-ink-secondary text-[13.5px] mb-5">
            Suivi des modèles déployés — un seul modèle actif en production à la fois.
          </div>

          {loading && <div className="text-ink-secondary">Chargement...</div>}

          {!loading && (
            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
              {models.map((m) => (
                <div
                  key={m.id}
                  className={`relative bg-surface rounded-xl p-5 ${m.is_active ? "border-[1.5px] border-brand" : "border border-line"}`}
                >
                  {m.is_active && (
                    <div className="absolute -top-2.5 right-4 bg-brand text-white text-[10.5px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">
                      Actif
                    </div>
                  )}
                  <div className="font-display text-[19px] font-semibold mb-0.5">
                    {ALGO_LABELS[m.algorithm] || m.algorithm}
                  </div>
                  <div className="text-[12.5px] text-ink-secondary mb-4">
                    Version {m.version} · Entraîné le {formatDate(m.trained_at)}
                  </div>

                  <div className="grid gap-3">
                    <MetricBar label="Precision" value={m.precision_score} />
                    <MetricBar label="Recall" value={m.recall_score} />
                    <MetricBar label="F1-score" value={m.f1_score} />
                    <MetricBar label="AUC-ROC" value={m.auc_roc} />
                  </div>

                  {!m.is_active && (
                    <button className="mt-4 w-full py-2.5 rounded-lg border border-line bg-surface text-[12.5px] font-semibold">
                      Activer ce modèle
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
