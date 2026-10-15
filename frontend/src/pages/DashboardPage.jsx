import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../services/api";
import Layout from "../components/Layout";
import StatTile from "../components/StatTile";

const STATUS_META = [
  { key: "legitimate", label: "Legitimes", color: "#2FA36B" },
  { key: "pending", label: "En attente", color: "#E8A33D" },
  { key: "under_review", label: "En examen", color: "#2F6FED" },
  { key: "fraudulent", label: "Frauduleuses", color: "#D64545" },
];

const numberFormatter = new Intl.NumberFormat("fr-FR");
const amountFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

async function sumAmounts(status) {
  let total = 0;
  let url = "/transactions/";
  let params = { status };

  while (url) {
    const { data } = await api.get(url, { params });
    total += data.results.reduce((acc, t) => acc + Number(t.amount), 0);
    url = data.next;
    params = undefined;
  }
  return total;
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        const [totalRes, alertsRes, ...statusResults] = await Promise.all([
          api.get("/transactions/"),
          api.get("/alerts/", { params: { status: "open" } }),
          ...STATUS_META.map((s) => api.get("/transactions/", { params: { status: s.key } })),
        ]);

        const [fraudulentAmount, underReviewAmount] = await Promise.all([
          sumAmounts("fraudulent"),
          sumAmounts("under_review"),
        ]);

        if (cancelled) return;

        const total = totalRes.data.count;
        const fraudulentCount = statusResults[STATUS_META.findIndex((s) => s.key === "fraudulent")].data.count;

        setStats({
          total,
          fraudRate: total > 0 ? (fraudulentCount / total) * 100 : 0,
          amountAtRisk: fraudulentAmount + underReviewAmount,
          activeAlerts: alertsRes.data.count,
          byStatus: STATUS_META.map((meta, i) => ({
            ...meta,
            count: statusResults[i].data.count,
          })),
        });
      } catch (err) {
        if (!cancelled) setError("Impossible de charger les indicateurs du dashboard.");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Dashboard</h1>

      {error && (
        <div className="mt-6 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>
      )}

      {!error && !stats && (
        <p className="mt-6 text-sm text-ink-secondary">Chargement des indicateurs...</p>
      )}

      {stats && (
        <>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Volume total" value={numberFormatter.format(stats.total)} />
            <StatTile label="Taux de fraude" value={`${stats.fraudRate.toFixed(1)}%`} />
            <StatTile label="Montant a risque" value={amountFormatter.format(stats.amountAtRisk)} />
            <StatTile label="Alertes actives" value={numberFormatter.format(stats.activeAlerts)} />
          </div>

          <div className="mt-6 rounded-xl border border-line bg-surface p-6 shadow-sm">
            <h2 className="text-sm font-medium text-ink-primary">Transactions par statut</h2>
            <div className="mt-4 h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.byStatus} layout="vertical" margin={{ left: 8, right: 32, top: 8, bottom: 8 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={100}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#5B6472", fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(value) => [numberFormatter.format(value), "Transactions"]}
                    cursor={{ fill: "#F5F7FB" }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={22}>
                    {stats.byStatus.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                    <LabelList dataKey="count" position="right" fill="#101828" fontSize={12} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
