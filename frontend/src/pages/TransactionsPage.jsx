import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const CHANNEL_LABELS = { card: "Carte", mobile_money: "Mobile Money", transfer: "Virement", online: "En ligne" };
const STATUS_LABELS = { legitimate: "Légitime", fraudulent: "Frauduleuse", under_review: "En examen", pending: "En attente" };

function formatAmount(amount) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(parseFloat(amount))) + " F";
}
function formatDate(iso) {
  return new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user] = useState(mockUser);

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG
        ? await mockApi.getTransactions()
        : (await api.get("/transactions/")).data;
      setTransactions(data.results || []);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div style={{ display: "flex" }}>
      <Sidebar user={user} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar title="Transactions">
          <button style={{ padding: "10px 16px", border: "none", borderRadius: 9, background: "var(--brand)", color: "#fff", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 7 }}>
            <i className="ti ti-plus" /> Saisir une transaction
          </button>
        </Topbar>

        <div style={{ padding: 28 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--canvas)" }}>
                  {["ID Transaction", "Montant", "Marchand", "Canal", "Date", "Statut"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "13px 22px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", borderBottom: "1px solid var(--border)" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={6} style={{ padding: 22, color: "var(--text-secondary)" }}>Chargement...</td></tr>
                )}
                {!loading && transactions.map((t) => (
                  <tr key={t.id}>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)", fontWeight: 600, color: "var(--brand)" }}>#{t.transaction_id}</td>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>{formatAmount(t.amount)}</td>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)" }}>{t.merchant}</td>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{CHANNEL_LABELS[t.channel] || t.channel}</td>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)" }}>{formatDate(t.timestamp)}</td>
                    <td style={{ padding: "14px 22px", borderBottom: "1px solid var(--border)" }}>
                      <span className={`status-badge ${t.status}`}>
                        <span className="dot" />{STATUS_LABELS[t.status] || t.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
