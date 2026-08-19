import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

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
      await api.post(`/alerts/${selected.id}/confirm/`); // deja implemente cote backend
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
    <div style={{ display: "flex" }}>
      <Sidebar user={user} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar title="Alertes" />

        <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
          <div style={{ width: 340, borderRight: "1px solid var(--border)", overflowY: "auto", flexShrink: 0 }}>
            {alerts.map((a) => (
              <div
                key={a.id}
                onClick={() => setSelected(a)}
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--border)",
                  cursor: "pointer",
                  background: selected?.id === a.id ? "var(--brand-soft)" : "transparent",
                  borderLeft: selected?.id === a.id ? "3px solid var(--brand)" : "3px solid transparent",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span className={`severity-badge ${a.severity}`}>
                    {a.severity === "critical" && "Critique"}
                    {a.severity === "high" && "Élevée"}
                    {a.severity === "medium" && "Moyenne"}
                    {a.severity === "low" && "Faible"}
                  </span>
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 3 }}>
                  #{a.transaction?.transaction_id} — {formatAmount(a.transaction?.amount || 0)}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Score {(a.fraud_probability * 100).toFixed(0)}% · {a.status}
                </div>
              </div>
            ))}
          </div>

          <div style={{ flex: 1, padding: "28px 32px", overflowY: "auto" }}>
            {!selected ? (
              <div style={{ color: "var(--text-secondary)" }}>Sélectionnez une alerte</div>
            ) : (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
                  <div>
                    <h2 style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 600 }}>
                      Alerte #{selected.transaction?.transaction_id}
                    </h2>
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                      Statut actuel : <strong>{selected.status}</strong>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button onClick={handleReject} style={{ padding: "10px 16px", borderRadius: 9, fontSize: 13, fontWeight: 600, border: "1px solid var(--border)", background: "var(--surface)", cursor: "pointer" }}>
                      <i className="ti ti-x" /> Rejeter
                    </button>
                    <button onClick={handleConfirm} style={{ padding: "10px 16px", borderRadius: 9, fontSize: 13, fontWeight: 600, border: "1px solid var(--danger)", background: "var(--danger)", color: "#fff", cursor: "pointer" }}>
                      <i className="ti ti-check" /> Confirmer la fraude
                    </button>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 28, alignItems: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, padding: 24, marginBottom: 20 }}>
                  <div style={{ width: 100, height: 100, borderRadius: "50%", background: `conic-gradient(var(--danger) 0deg ${selected.fraud_probability * 360}deg, var(--border) ${selected.fraud_probability * 360}deg 360deg)`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: 76, height: 76, borderRadius: "50%", background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 600, color: "var(--danger)" }}>
                      {(selected.fraud_probability * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>Probabilité de fraude</h3>
                    <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: 420 }}>
                      Score produit par le modèle ML actif à partir des caractéristiques de la transaction.
                    </p>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 20 }}>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: 6 }}>Montant</div>
                    <div style={{ fontSize: 15, fontWeight: 600 }}>{formatAmount(selected.transaction?.amount || 0)}</div>
                  </div>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: 6 }}>Appareil</div>
                    <div style={{ fontSize: 15, fontWeight: 600 }}>{selected.transaction?.device}</div>
                  </div>
                  <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: 6 }}>Localisation</div>
                    <div style={{ fontSize: 15, fontWeight: 600 }}>{selected.transaction?.location}</div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
