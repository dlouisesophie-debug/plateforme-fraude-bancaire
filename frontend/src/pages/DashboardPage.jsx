import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const styles = {
  main: { flex: 1, display: "flex", flexDirection: "column", minWidth: 0 },
  content: { padding: 28 },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 },
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, padding: 20 },
  kpiNum: { fontFamily: "var(--font-display)", fontSize: 30, fontWeight: 600, letterSpacing: "-0.01em" },
  kpiLabel: { fontSize: 12.5, color: "var(--text-secondary)", marginTop: 4 },
};

function formatNumber(n) {
  return new Intl.NumberFormat("fr-FR").format(n);
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [user] = useState(mockUser); // TODO Etudiant 3 : recuperer via /api/auth/me/ une fois dispo

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG
        ? await mockApi.getDashboardKpis()
        : (await api.get("/dashboard/kpis/")).data; // TODO Etudiant 1 : endpoint a exposer
      setKpis(data);
    }
    load();
  }, []);

  return (
    <div style={{ display: "flex" }}>
      <Sidebar user={user} />
      <div style={styles.main}>
        <Topbar title="Dashboard">
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--canvas)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", width: 220, color: "var(--text-secondary)", fontSize: 13 }}>
            <i className="ti ti-search" /> Rechercher...
          </div>
        </Topbar>

        <div style={styles.content}>
          <div style={{ color: "var(--text-secondary)", fontSize: 13.5, marginBottom: 24 }}>
            Vue d'ensemble de l'activité — 7 derniers jours
          </div>

          {!kpis ? (
            <div style={{ color: "var(--text-secondary)" }}>Chargement...</div>
          ) : (
            <div style={styles.kpiGrid}>
              <div style={styles.card}>
                <div style={styles.kpiNum}>{formatNumber(kpis.transaction_volume)}</div>
                <div style={styles.kpiLabel}>Volume de transactions</div>
              </div>
              <div style={styles.card}>
                <div style={styles.kpiNum}>{kpis.fraud_rate}%</div>
                <div style={styles.kpiLabel}>Taux de fraude</div>
              </div>
              <div style={styles.card}>
                <div style={styles.kpiNum}>{formatNumber(kpis.amount_at_risk / 1000000)}M FCFA</div>
                <div style={styles.kpiLabel}>Montant à risque</div>
              </div>
              <div style={styles.card}>
                <div style={styles.kpiNum}>{kpis.active_alerts}</div>
                <div style={styles.kpiLabel}>Alertes actives</div>
              </div>
            </div>
          )}

          {kpis && (
            <div style={{ ...styles.card, marginTop: 8 }}>
              <div style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 18 }}>Évolution des transactions</div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 120 }}>
                {kpis.weekly_volume.map((d) => (
                  <div key={d.day} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                    <div style={{ width: "100%", height: d.value, background: "var(--brand)", borderRadius: "5px 5px 0 0" }} />
                    <div style={{ fontSize: 10.5, color: "var(--text-secondary)" }}>{d.day}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TODO Etudiant 3 : remplacer ce bar chart CSS par un vrai graphique
              Recharts (LineChart/BarChart) une fois le design valide, et ajouter
              le donut de repartition par canal (kpis.channel_breakdown) */}
        </div>
      </div>
    </div>
  );
}
