import { useEffect, useState } from "react";
import api, { downloadFile } from "../services/api";
import Layout from "../components/Layout";
import Notice from "../components/Notice";
import { REPORT_TYPE_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS, INPUT_CLASS, LABEL_CLASS, PRIMARY_BUTTON } from "../constants/ui";
import { apiErrorMessage, asList, formatDate, formatDateTime } from "../utils/format";

const EMPTY_REPORT = { title: "", type: "pdf", period_start: "", period_end: "" };

function reportFilename(report) {
  const slug = (report.title || `rapport-${report.id}`).replace(/[^\w-]+/g, "_");
  return `${slug}.${report.type || "pdf"}`;
}

export default function ReportsPage() {
  const [form, setForm] = useState(EMPTY_REPORT);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [error, setError] = useState(null);
  const [created, setCreated] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/reports/")
      .then((res) => {
        if (!cancelled) setReports(asList(res.data));
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger l'historique des rapports.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setCreated(null);
    try {
      const payload = { ...form, period_start: form.period_start || null, period_end: form.period_end || null };
      const { data } = await api.post("/reports/", payload);
      setReports((prev) => [data, ...prev]);
      setCreated(data);
      setForm(EMPTY_REPORT);
    } catch (err) {
      setError(apiErrorMessage(err, "Génération du rapport impossible."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDownload(report) {
    setDownloadingId(report.id);
    setError(null);
    try {
      await downloadFile(report.download_url, { filename: reportFilename(report) });
    } catch {
      setError("Téléchargement impossible.");
    } finally {
      setDownloadingId(null);
    }
  }

  const downloadButton = (report, className) =>
    report.download_url ? (
      <button type="button" onClick={() => handleDownload(report)} disabled={downloadingId === report.id} className={className}>
        {downloadingId === report.id ? "Téléchargement..." : "Télécharger"}
      </button>
    ) : (
      <span className="text-xs text-ink-secondary">Fichier indisponible</span>
    );

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Rapports</h1>

      <form onSubmit={handleSubmit} className={`${CARD_CLASS} mt-6`}>
        <h2 className="text-sm font-medium text-ink-primary">Générer un rapport</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2 lg:col-span-1">
            <label htmlFor="report-title" className={LABEL_CLASS}>
              Titre
            </label>
            <input id="report-title" name="title" value={form.title} onChange={handleChange} required className={INPUT_CLASS} placeholder="Rapport mensuel" />
          </div>
          <div>
            <label htmlFor="report-type" className={LABEL_CLASS}>
              Format
            </label>
            <select id="report-type" name="type" value={form.type} onChange={handleChange} className={INPUT_CLASS}>
              {REPORT_TYPE_CHOICES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="report-start" className={LABEL_CLASS}>
              Début de période
            </label>
            <input id="report-start" type="date" name="period_start" value={form.period_start} max={form.period_end || undefined} onChange={handleChange} className={INPUT_CLASS} />
          </div>
          <div>
            <label htmlFor="report-end" className={LABEL_CLASS}>
              Fin de période
            </label>
            <input id="report-end" type="date" name="period_end" value={form.period_end} min={form.period_start || undefined} onChange={handleChange} className={INPUT_CLASS} />
          </div>
        </div>
        <button type="submit" disabled={submitting} className={`${PRIMARY_BUTTON} mt-4`}>
          {submitting ? "Génération..." : "Générer"}
        </button>
      </form>

      {created && (
        <Notice tone="success" className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>Rapport « {created.title} » généré.</span>
            {downloadButton(created, "rounded-xl bg-success px-3 py-1.5 text-xs font-medium text-white hover:bg-success/90 disabled:opacity-50")}
          </div>
        </Notice>
      )}
      <Notice className="mt-4">{error}</Notice>

      <h2 className="mt-8 text-sm font-medium text-ink-primary">Historique</h2>
      <div className="mt-3 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <ul className="divide-y divide-line">
          {reports.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink-primary">
                  {r.title} <span className="text-xs font-normal text-ink-secondary">({labelFor(REPORT_TYPE_CHOICES, r.type)})</span>
                </p>
                <p className="text-xs text-ink-secondary">
                  {r.period_start || r.period_end
                    ? `Du ${formatDate(r.period_start)} au ${formatDate(r.period_end)}`
                    : "Toute la période"}{" "}
                  · généré le {formatDateTime(r.created_at)}
                </p>
              </div>
              {downloadButton(r, "rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:opacity-50")}
            </li>
          ))}
          {!loading && reports.length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">Aucun rapport généré</li>
          )}
          {loading && <li className="px-4 py-6 text-center text-sm text-ink-secondary">Chargement...</li>}
        </ul>
      </div>
    </Layout>
  );
}
