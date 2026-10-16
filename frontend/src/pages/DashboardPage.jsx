import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import Layout from "../components/Layout";
import StatTile from "../components/StatTile";
import DateRangeFilter from "../components/DateRangeFilter";
import Notice from "../components/Notice";
import { CHANNEL_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS } from "../constants/ui";
import { formatAmount, formatDate, formatNumber, formatPercent } from "../utils/format";

const COLORS = {
  brand: "#2F6FED",
  danger: "#D64545",
  success: "#2FA36B",
  warning: "#E8A33D",
  axis: "#5B6472",
  grid: "#E3E7EF",
  ink: "#101828",
  cursor: "#F5F7FB",
};

const STATUS_META = [
  { key: "legitimate", label: "Légitimes", color: COLORS.success },
  { key: "pending", label: "En attente", color: COLORS.warning },
  { key: "under_review", label: "En examen", color: COLORS.brand },
  { key: "fraudulent", label: "Frauduleuses", color: COLORS.danger },
];

const AXIS_TICK = { fill: COLORS.axis, fontSize: 12 };

// by_status peut arriver en objet { legitimate: 12 } ou en liste [{ status, count }].
function statusCount(byStatus, key) {
  if (Array.isArray(byStatus)) return Number(byStatus.find((s) => s.status === key)?.count ?? 0);
  return Number(byStatus?.[key] ?? 0);
}

// Matrice de confusion : { tp, fp, tn, fn } (ou noms longs true_positive...).
function readConfusion(cm) {
  if (!cm) return null;
  const pick = (short, long) => Number(cm[short] ?? cm[long] ?? 0);
  return {
    tp: pick("tp", "true_positive"),
    fp: pick("fp", "false_positive"),
    tn: pick("tn", "true_negative"),
    fn: pick("fn", "false_negative"),
  };
}

function normalizeStats(data) {
  // Les KPIs sont regroupés sous "kpis" dans la réponse du backend.
  const kpis = data.kpis || {};
  const total = Number(kpis.total_transactions ?? 0);
  const byStatus = STATUS_META.map((meta) => ({ ...meta, count: statusCount(data.by_status, meta.key) }));
  const fraudulent = byStatus.find((s) => s.key === "fraudulent").count;
  return {
    total,
    fraudRate: kpis.fraud_rate ?? (total > 0 ? (fraudulent / total) * 100 : 0),
    amountAtRisk: kpis.amount_at_risk ?? 0,
    openAlerts: kpis.active_alerts ?? 0,
    byStatus,
    daily: (data.daily || []).map((d) => ({
      date: d.date ?? d.day,
      total: Number(d.total ?? d.count ?? 0),
      fraudulent: Number(d.fraudulent ?? d.frauds ?? 0),
    })),
    byChannel: (data.by_channel || []).map((c) => ({
      label: labelFor(CHANNEL_CHOICES, c.channel),
      total: Number(c.total ?? c.count ?? 0),
      fraudulent: Number(c.fraudulent ?? c.frauds ?? 0),
    })),
    confusion: readConfusion(data.confusion_matrix),
  };
}

function ChartCard({ title, subtitle, children, empty }) {
  return (
    <section className={CARD_CLASS}>
      <h2 className="text-sm font-medium text-ink-primary">{title}</h2>
      {subtitle && <p className="mt-0.5 text-xs text-ink-secondary">{subtitle}</p>}
      {empty ? (
        <p className="mt-6 text-sm text-ink-secondary">Aucune donnée sur la période.</p>
      ) : (
        <div className="mt-4 h-64 w-full">{children}</div>
      )}
    </section>
  );
}

function ConfusionMatrix({ confusion }) {
  const { tp, fp, tn, fn } = confusion;
  const precision = tp + fp > 0 ? (tp / (tp + fp)) * 100 : null;
  const recall = tp + fn > 0 ? (tp / (tp + fn)) * 100 : null;
  const cell = (value, label, good) => (
    <div className={`rounded-xl p-4 text-center ${good ? "bg-success-soft text-success" : "bg-danger-soft text-danger"}`}>
      <p className="text-2xl font-semibold tabular-nums">{formatNumber(value)}</p>
      <p className="mt-1 text-xs font-medium">{label}</p>
    </div>
  );

  return (
    <section className={CARD_CLASS}>
      <h2 className="text-sm font-medium text-ink-primary">Matrice de confusion</h2>
      <p className="mt-0.5 text-xs text-ink-secondary">Prédictions du modèle comparées aux décisions des analystes</p>
      <div className="mt-4 grid grid-cols-[auto_1fr_1fr] items-center gap-2 text-xs text-ink-secondary">
        <span />
        <span className="text-center font-medium">Prédit : fraude</span>
        <span className="text-center font-medium">Prédit : légitime</span>
        <span className="pr-2 text-right font-medium">Réel : fraude</span>
        {cell(tp, "Vrais positifs", true)}
        {cell(fn, "Faux négatifs", false)}
        <span className="pr-2 text-right font-medium">Réel : légitime</span>
        {cell(fp, "Faux positifs", false)}
        {cell(tn, "Vrais négatifs", true)}
      </div>
      <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <div className="flex gap-2">
          <dt className="text-ink-secondary">Précision</dt>
          <dd className="font-medium text-ink-primary">{precision === null ? "—" : formatPercent(precision)}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-ink-secondary">Rappel</dt>
          <dd className="font-medium text-ink-primary">{recall === null ? "—" : formatPercent(recall)}</dd>
        </div>
      </dl>
    </section>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [period, setPeriod] = useState({ after: "", before: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get("/dashboard/stats/", {
        params: { date_after: period.after || undefined, date_before: period.before || undefined },
      })
      .then((res) => {
        if (!cancelled) setStats(normalizeStats(res.data));
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger les indicateurs du dashboard.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [period.after, period.before]);

  return (
    <Layout>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold text-ink-primary">Dashboard</h1>
        <DateRangeFilter after={period.after} before={period.before} onChange={setPeriod} />
      </div>

      <Notice className="mt-6">{error}</Notice>

      {!error && !stats && <p className="mt-6 text-sm text-ink-secondary">Chargement des indicateurs...</p>}

      {stats && (
        <div className={`transition-opacity ${loading ? "opacity-60" : ""}`}>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Volume total" value={formatNumber(stats.total)} />
            <StatTile label="Taux de fraude" value={formatPercent(stats.fraudRate)} />
            <StatTile label="Montant à risque" value={formatAmount(stats.amountAtRisk)} />
            <StatTile label="Alertes ouvertes" value={formatNumber(stats.openAlerts)} />
          </div>

          <div className="mt-4">
            <ChartCard title="Transactions par jour" empty={stats.daily.length === 0}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.daily} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={formatDate} tick={AXIS_TICK} tickLine={false} axisLine={false} minTickGap={24} />
                  <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} />
                  <Tooltip labelFormatter={formatDate} formatter={(value, name) => [formatNumber(value), name]} />
                  <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="total" name="Total" stroke={COLORS.brand} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="fraudulent" name="Frauduleuses" stroke={COLORS.danger} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard title="Transactions par canal" empty={stats.byChannel.length === 0}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.byChannel} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} interval={0} />
                  <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} />
                  <Tooltip formatter={(value, name) => [formatNumber(value), name]} cursor={{ fill: COLORS.cursor }} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="total" name="Total" fill={COLORS.brand} radius={[4, 4, 0, 0]} maxBarSize={28} />
                  <Bar dataKey="fraudulent" name="Frauduleuses" fill={COLORS.danger} radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Transactions par statut" empty={stats.total === 0}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.byStatus} layout="vertical" margin={{ left: 8, right: 32, top: 8, bottom: 8 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="label" width={100} tickLine={false} axisLine={false} tick={AXIS_TICK} />
                  <Tooltip formatter={(value) => [formatNumber(value), "Transactions"]} cursor={{ fill: COLORS.cursor }} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={22}>
                    {stats.byStatus.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                    <LabelList dataKey="count" position="right" fill={COLORS.ink} fontSize={12} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {stats.confusion && (
            <div className="mt-4">
              <ConfusionMatrix confusion={stats.confusion} />
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
