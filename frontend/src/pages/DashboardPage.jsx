import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

function formatNumber(n) {
  return new Intl.NumberFormat("fr-FR").format(n);
}

const KPI_CARDS = [
  { key: "transaction_volume", label: "Volume de transactions", icon: "ti-arrows-exchange", iconBg: "bg-brand-soft", iconFg: "text-brand", format: (v) => formatNumber(v) },
  { key: "fraud_rate", label: "Taux de fraude", icon: "ti-percentage", iconBg: "bg-danger-soft", iconFg: "text-danger", format: (v) => `${v}%` },
  { key: "amount_at_risk", label: "Montant à risque", icon: "ti-cash-off", iconBg: "bg-warning-soft", iconFg: "text-warning", format: (v) => `${formatNumber(Math.round(v / 1000000))}M FCFA` },
  { key: "active_alerts", label: "Alertes actives", icon: "ti-bell-ringing", iconBg: "bg-success-soft", iconFg: "text-success", format: (v) => v },
];

export default function DashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [user] = useState(mockUser);

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG
        ? await mockApi.getDashboardKpis()
        : (await api.get("/dashboard/kpis/")).data;
      setKpis(data);
    }
    load();
  }, []);

  return (
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Dashboard">
          <div className="flex items-center gap-2 bg-canvas border border-line rounded-lg px-3 py-2 w-56 text-ink-secondary text-sm">
            <i className="ti ti-search" /> Rechercher...
          </div>
        </Topbar>

        <div className="p-7">
          <div className="text-ink-secondary text-[13.5px] mb-6">
            Vue d'ensemble de l'activité — 7 derniers jours
          </div>

          {!kpis ? (
            <div className="text-ink-secondary">Chargement...</div>
          ) : (
            <div className="grid grid-cols-4 gap-4 mb-6">
              {KPI_CARDS.map((c) => (
                <div key={c.key} className="bg-surface border border-line rounded-xl p-5">
                  <div className={`w-[34px] h-[34px] rounded-[9px] flex items-center justify-center mb-3.5 ${c.iconBg} ${c.iconFg}`}>
                    <i className={`ti ${c.icon}`} />
                  </div>
                  <div className="font-display text-[30px] font-semibold tracking-tight tabular-nums">
                    {c.format(kpis[c.key])}
                  </div>
                  <div className="text-[12.5px] text-ink-secondary mt-1">{c.label}</div>
                </div>
              ))}
            </div>
          )}

          {kpis && (
            <div className="grid grid-cols-[1.6fr_1fr] gap-4">
              <div className="bg-surface border border-line rounded-xl p-5">
                <div className="text-[14.5px] font-semibold mb-4">Évolution des transactions</div>
                <div className="flex items-end gap-2.5 h-32">
                  {kpis.weekly_volume.map((d) => (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1.5">
                      <div className="w-full bg-brand rounded-t" style={{ height: `${d.value}px` }} />
                      <div className="text-[10.5px] text-ink-secondary">{d.day}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-surface border border-line rounded-xl p-5">
                <div className="text-[14.5px] font-semibold mb-4">Répartition par canal</div>
                <div className="flex flex-col gap-2">
                  {kpis.channel_breakdown.map((c) => (
                    <div key={c.channel} className="flex items-center gap-2 text-xs">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{
                          background: c.channel === "card" ? "#2F6FED" : c.channel === "mobile_money" ? "#E8A33D" : "#D64545",
                        }}
                      />
                      {c.label}
                      <span className="ml-auto text-ink-secondary">{c.percent}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
