import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const CHANNEL_LABELS = { card: "Carte", mobile_money: "Mobile Money", transfer: "Virement", online: "En ligne" };
const STATUS_LABELS = { legitimate: "Légitime", fraudulent: "Frauduleuse", under_review: "En examen", pending: "En attente" };
const STATUS_CLASSES = {
  legitimate: "bg-success-soft text-success",
  fraudulent: "bg-danger-soft text-danger",
  under_review: "bg-warning-soft text-[#B5780F]",
  pending: "bg-canvas text-ink-secondary",
};

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
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Transactions">
          <button className="flex items-center gap-1.5 px-4 py-2.5 rounded-[9px] bg-brand text-white text-[13px] font-semibold">
            <i className="ti ti-plus" /> Saisir une transaction
          </button>
        </Topbar>

        <div className="p-7">
          <div className="bg-surface border border-line rounded-xl overflow-hidden">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="bg-canvas">
                  {["ID Transaction", "Montant", "Marchand", "Canal", "Date", "Statut"].map((h) => (
                    <th key={h} className="text-left px-5 py-3.5 text-[11px] uppercase tracking-wide text-ink-secondary border-b border-line">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={6} className="p-5 text-ink-secondary">Chargement...</td></tr>
                )}
                {!loading && transactions.map((t) => (
                  <tr key={t.id}>
                    <td className="px-5 py-3.5 border-b border-line font-semibold text-brand">#{t.transaction_id}</td>
                    <td className="px-5 py-3.5 border-b border-line font-semibold tabular-nums">{formatAmount(t.amount)}</td>
                    <td className="px-5 py-3.5 border-b border-line">{t.merchant}</td>
                    <td className="px-5 py-3.5 border-b border-line text-ink-secondary">{CHANNEL_LABELS[t.channel] || t.channel}</td>
                    <td className="px-5 py-3.5 border-b border-line">{formatDate(t.timestamp)}</td>
                    <td className="px-5 py-3.5 border-b border-line">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11.5px] font-semibold ${STATUS_CLASSES[t.status] || STATUS_CLASSES.pending}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        {STATUS_LABELS[t.status] || t.status}
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
