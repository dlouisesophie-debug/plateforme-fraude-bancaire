import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

const TYPE_ICON = { pdf: "ti-file-type-pdf", csv: "ti-file-type-csv" };
const TYPE_COLOR = { pdf: "text-danger", csv: "text-success" };

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [user] = useState(mockUser);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const data = USE_MOCKS_FLAG ? await mockApi.getReports() : (await api.get("/reports/")).data;
    setReports(data.results || []);
    setLoading(false);
  }

  async function handleGenerate(type) {
    setGenerating(true);
    const payload = { title: `Rapport ${type.toUpperCase()} — ${new Date().toLocaleDateString("fr-FR")}`, type };
    if (USE_MOCKS_FLAG) {
      const newReport = await mockApi.generateReport(payload);
      setReports((prev) => [newReport, ...prev]);
    } else {
      await api.post("/reports/", payload);
      await load();
    }
    setGenerating(false);
  }

  return (
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Rapports">
          <button
            onClick={() => handleGenerate("pdf")}
            disabled={generating}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-[9px] border border-line bg-surface text-[13px] font-semibold disabled:opacity-60"
          >
            <i className="ti ti-file-type-pdf" /> Générer PDF
          </button>
          <button
            onClick={() => handleGenerate("csv")}
            disabled={generating}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-[9px] bg-brand text-white text-[13px] font-semibold disabled:opacity-60"
          >
            <i className="ti ti-file-type-csv" /> Générer CSV
          </button>
        </Topbar>

        <div className="p-7">
          <div className="text-ink-secondary text-[13.5px] mb-5">
            Rapports générés — période, montants et alertes couverts par chaque export.
          </div>

          {loading && <div className="text-ink-secondary">Chargement...</div>}

          {!loading && (
            <div className="grid gap-3">
              {reports.map((r) => (
                <div key={r.id} className="bg-surface border border-line rounded-xl p-4 flex items-center gap-4">
                  <div className="w-[42px] h-[42px] rounded-[10px] bg-canvas flex items-center justify-center shrink-0">
                    <i className={`ti ${TYPE_ICON[r.type]} text-xl ${TYPE_COLOR[r.type]}`} />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold">{r.title}</div>
                    <div className="text-[12.5px] text-ink-secondary mt-0.5">
                      {r.period_start && r.period_end
                        ? `Période du ${formatDate(r.period_start)} au ${formatDate(r.period_end)}`
                        : "Période non spécifiée"}
                      {" · "}Généré le {formatDate(r.created_at)}
                    </div>
                  </div>
                  <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-line bg-surface text-[12.5px] font-semibold">
                    <i className="ti ti-download" /> Télécharger
                  </button>
                </div>
              ))}
              {reports.length === 0 && (
                <div className="text-ink-secondary text-[13.5px] text-center py-10">
                  Aucun rapport généré pour le moment.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
