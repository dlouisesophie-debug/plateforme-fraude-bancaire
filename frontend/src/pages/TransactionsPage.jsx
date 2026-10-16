import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { downloadFile } from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import ScoreBadge from "../components/ScoreBadge";
import Pagination from "../components/Pagination";
import DateRangeFilter from "../components/DateRangeFilter";
import Notice from "../components/Notice";
import { useAuth } from "../hooks/useAuth";
import { NAV_ITEMS, canAccess } from "../constants/roles";
import { CHANNEL_CHOICES, TRANSACTION_STATUS_CHOICES, labelFor } from "../constants/choices";
import { INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON, SELECT_CLASS } from "../constants/ui";
import { formatAmount, formatDateTime } from "../utils/format";

const PAGE_SIZE = 20;
const COLUMNS = 6;

export default function TransactionsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [period, setPeriod] = useState({ after: "", before: "" });
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  const canCreate = canAccess(user, NAV_ITEMS.find((i) => i.to === "/transactions/new").roles);

  // Mêmes filtres pour la liste et pour l'export CSV.
  const filters = {
    status: status || undefined,
    channel: channel || undefined,
    search: search || undefined,
    date_after: period.after || undefined,
    date_before: period.before || undefined,
  };

  // La recherche part 300 ms après la dernière frappe.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get("/transactions/", { params: { page, ...filters } })
      .then((res) => {
        if (cancelled) return;
        setTransactions(res.data.results || []);
        setCount(res.data.count || 0);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger les transactions.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, status, channel, search, period.after, period.before]);

  function handleFilterChange(setter) {
    return (e) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  function handlePeriodChange(next) {
    setPeriod(next);
    setPage(1);
  }

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      await downloadFile("/transactions/export/", { params: filters, filename: "transactions.csv" });
    } catch {
      setError("Export CSV impossible.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <Layout>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold text-ink-primary">Transactions</h1>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={handleExport} disabled={exporting} className={SECONDARY_BUTTON}>
            {exporting ? "Export en cours..." : "Exporter CSV"}
          </button>
          {canCreate && (
            <Link to="/transactions/new" className={PRIMARY_BUTTON}>
              Nouvelle transaction
            </Link>
          )}
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Rechercher (ID, commerçant, lieu...)"
          aria-label="Rechercher une transaction"
          className={`${INPUT_CLASS} sm:w-72`}
        />
        <select value={status} onChange={handleFilterChange(setStatus)} aria-label="Statut" className={SELECT_CLASS}>
          <option value="">Tous les statuts</option>
          {TRANSACTION_STATUS_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select value={channel} onChange={handleFilterChange(setChannel)} aria-label="Canal" className={SELECT_CLASS}>
          <option value="">Tous les canaux</option>
          {CHANNEL_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <DateRangeFilter after={period.after} before={period.before} onChange={handlePeriodChange} />
      </div>

      <Notice className="mt-4">{error}</Notice>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas text-xs font-medium uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Montant</th>
                <th className="px-4 py-3">Canal</th>
                <th className="px-4 py-3">Score (%)</th>
                <th className="px-4 py-3">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {!loading &&
                transactions.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/transactions/${t.id}`)}
                    className="cursor-pointer text-ink-primary transition-colors hover:bg-canvas"
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-medium">
                      <Link to={`/transactions/${t.id}`} onClick={(e) => e.stopPropagation()} className="hover:text-brand">
                        {t.transaction_id}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-secondary">{formatDateTime(t.timestamp)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">{formatAmount(t.amount)}</td>
                    <td className="whitespace-nowrap px-4 py-3">{labelFor(CHANNEL_CHOICES, t.channel)}</td>
                    <td className="px-4 py-3">
                      <ScoreBadge value={t.fraud_probability} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={t.status} label={labelFor(TRANSACTION_STATUS_CHOICES, t.status)} />
                    </td>
                  </tr>
                ))}
              {!loading && transactions.length === 0 && !error && (
                <tr>
                  <td colSpan={COLUMNS} className="px-4 py-6 text-center text-ink-secondary">
                    Aucune transaction
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={COLUMNS} className="px-4 py-6 text-center text-ink-secondary">
                    Chargement...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {!loading && count > 0 && (
          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />
        )}
      </div>
    </Layout>
  );
}
