import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const SEVERITY_LABELS = { critical: "Critique", high: "Élevée", medium: "Moyenne", low: "Faible" };
const SEVERITY_CLASSES = {
  critical: "bg-danger-soft text-danger",
  high: "bg-warning-soft text-[#B5780F]",
  medium: "bg-brand-soft text-brand",
  low: "bg-canvas text-ink-secondary",
};

function formatAmount(amount) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(parseFloat(amount))) + " F";
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [user] = useState(mockUser);

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG
        ? await mockApi.getAlerts()
        : (await api.get("/alerts/")).data;
      const results = data.results || [];
      setAlerts(results);
      setSelected(results[0] || null);
    }
    load();
  }, []);

  async function handleConfirm() {
    if (!selected) return;
    if (USE_MOCKS_FLAG) {
      await mockApi.confirmAlert(selected.id);
    } else {
      await api.post(`/alerts/${selected.id}/confirm/`);
    }
    setAlerts((prev) => prev.map((a) => (a.id === selected.id ? { ...a, status: "confirmed" } : a)));
  }

  async function handleReject() {
    if (!selected) return;
    if (USE_MOCKS_FLAG) {
      await mockApi.rejectAlert(selected.id);
    } else {
      await api.post(`/alerts/${selected.id}/reject/`);
    }
    setAlerts((prev) => prev.map((a) => (a.id === selected.id ? { ...a, status: "rejected" } : a)));
  }

  return (
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Alertes" />

        <div className="flex-1 flex min-h-0">
          <div className="w-[340px] shrink-0 border-r border-line overflow-y-auto">
            {alerts.map((a) => (
              <div
                key={a.id}
                onClick={() => setSelected(a)}
                className={`px-5 py-4 border-b border-line cursor-pointer border-l-[3px] ${
                  selected?.id === a.id ? "bg-brand-soft border-l-brand" : "border-l-transparent"
                }`}
              >
                <div className="flex justify-between mb-1.5">
                  <span className={`text-[10.5px] font-bold uppercase tracking-wide px-2 py-1 rounded-md ${SEVERITY_CLASSES[a.severity]}`}>
                    {SEVERITY_LABELS[a.severity]}
                  </span>
                </div>
                <div className="text-[13.5px] font-semibold mb-0.5">
                  #{a.transaction?.transaction_id} — {formatAmount(a.transaction?.amount || 0)}
                </div>
                <div className="text-xs text-ink-secondary">
                  Score {(a.fraud_probability * 100).toFixed(0)}% · {a.status}
                </div>
              </div>
            ))}
          </div>

          <div className="flex-1 p-8 px-9 overflow-y-auto">
            {!selected ? (
              <div className="text-ink-secondary">Sélectionnez une alerte</div>
            ) : (
              <>
                <div className="flex justify-between mb-6">
                  <div>
                    <h2 className="font-display text-[22px] font-semibold">
                      Alerte #{selected.transaction?.transaction_id}
                    </h2>
                    <div className="text-[13px] text-ink-secondary mt-1">
                      Statut actuel : <strong>{selected.status}</strong>
                    </div>
                  </div>
                  <div className="flex gap-2.5">
                    <button
                      onClick={handleReject}
                      className="px-4 py-2.5 rounded-[9px] text-[13px] font-semibold border border-line bg-surface"
                    >
                      <i className="ti ti-x" /> Rejeter
                    </button>
                    <button
                      onClick={handleConfirm}
                      className="px-4 py-2.5 rounded-[9px] text-[13px] font-semibold border border-danger bg-danger text-white"
                    >
                      <i className="ti ti-check" /> Confirmer la fraude
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-7 bg-surface border border-line rounded-xl p-6 mb-5">
                  <div
                    className="w-[100px] h-[100px] rounded-full flex items-center justify-center shrink-0"
                    style={{
                      background: `conic-gradient(#D64545 0deg ${selected.fraud_probability * 360}deg, #E3E7EF ${selected.fraud_probability * 360}deg 360deg)`,
                    }}
                  >
                    <div className="w-[76px] h-[76px] rounded-full bg-surface flex items-center justify-center font-display text-xl font-semibold text-danger">
                      {(selected.fraud_probability * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <h3 className="text-[15px] font-semibold mb-1.5">Probabilité de fraude</h3>
                    <p className="text-[13px] text-ink-secondary leading-relaxed max-w-[420px]">
                      Score produit par le modèle ML actif à partir des caractéristiques de la transaction.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3.5">
                  {[
                    { label: "Montant", value: formatAmount(selected.transaction?.amount || 0) },
                    { label: "Appareil", value: selected.transaction?.device },
                    { label: "Localisation", value: selected.transaction?.location },
                  ].map((info) => (
                    <div key={info.label} className="bg-surface border border-line rounded-xl px-4 py-4">
                      <div className="text-[11px] text-ink-secondary uppercase mb-1.5">{info.label}</div>
                      <div className="text-[15px] font-semibold">{info.value}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
