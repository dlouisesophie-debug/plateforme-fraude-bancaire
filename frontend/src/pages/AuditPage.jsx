import { useEffect, useState } from "react";
import api from "../services/api";
import Layout from "../components/Layout";
import Pagination from "../components/Pagination";
import Notice from "../components/Notice";
import { AUDIT_ACTION_CHOICES, ROLE_CHOICES, labelFor } from "../constants/choices";
import { SELECT_CLASS } from "../constants/ui";
import { apiErrorMessage, asList, displayName, formatDateTime } from "../utils/format";

const PAGE_SIZE = 20;

const CHANGE_FIELD_LABELS = {
  role: "rôle",
  email: "e-mail",
  first_name: "prénom",
  last_name: "nom",
  username: "identifiant",
  is_active: "statut",
};

function formatChangeValue(field, value) {
  if (field === "role") return labelFor(ROLE_CHOICES, value);
  if (field === "is_active") return value ? "Actif" : "Inactif";
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function describeDetails(action, details) {
  if (!details) return "—";
  if (action === "LOGIN_SUCCESS" || action === "LOGIN_FAILED") {
    const parts = [`Identifiant : ${details.username ?? "—"}`];
    if (action === "LOGIN_FAILED" && details.status_code) parts.push(`Code : ${details.status_code}`);
    return parts.join(" · ");
  }
  if (action === "USER_CREATED" || action === "USER_DELETED") {
    return `${details.target_username ?? "—"} (${labelFor(ROLE_CHOICES, details.role)})`;
  }
  if (action === "USER_UPDATED") {
    const changes = Object.entries(details.changes || {}).map(
      ([field, change]) =>
        `${CHANGE_FIELD_LABELS[field] || field} : ${formatChangeValue(field, change.avant)} → ${formatChangeValue(field, change.apres)}`
    );
    return [details.target_username, ...changes].filter(Boolean).join(" · ");
  }
  return details.status_code ? `Code : ${details.status_code}` : "—";
}

export default function AuditPage() {
  const [entries, setEntries] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [userId, setUserId] = useState("");
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // GET /auth/users/ est paginé par 20 : on charge toutes les pages pour
  // retrouver le nom de l'auteur de chaque entrée.
  useEffect(() => {
    let cancelled = false;
    async function loadAllUsers() {
      let all = [];
      let next = { page: 1 };
      while (next) {
        const { data } = await api.get("/auth/users/", { params: next });
        all = all.concat(asList(data));
        next = data.next ? { page: next.page + 1 } : null;
      }
      return all;
    }
    loadAllUsers()
      .then((all) => {
        if (!cancelled) setUsers(all);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get("/audit/", { params: { page, action: action || undefined, user: userId || undefined } })
      .then((res) => {
        if (cancelled) return;
        setEntries(res.data.results || []);
        setCount(res.data.count || 0);
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessage(err, "Impossible de charger le journal d'audit."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, action, userId]);

  function handleFilterChange(setter) {
    return (e) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  // Compte supprimé depuis (plus dans /auth/users/) : on retombe sur "#<id>".
  function userLabel(id) {
    if (id === null || id === undefined) return "—";
    const found = users.find((u) => u.id === id);
    return found ? displayName(found) : `#${id}`;
  }

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-primary">Audit</h1>

      <div className="mt-6 flex flex-wrap gap-3">
        <select value={action} onChange={handleFilterChange(setAction)} aria-label="Action" className={SELECT_CLASS}>
          <option value="">Toutes les actions</option>
          {AUDIT_ACTION_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select value={userId} onChange={handleFilterChange(setUserId)} aria-label="Utilisateur" className={SELECT_CLASS}>
          <option value="">Tous les utilisateurs</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {displayName(u)}
            </option>
          ))}
        </select>
      </div>

      <Notice className="mt-4">{error}</Notice>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas text-xs font-medium uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Utilisateur</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Adresse IP</th>
                <th className="px-4 py-3">Détails</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {!loading &&
                entries.map((entry) => (
                  <tr key={entry.id} className="text-ink-primary">
                    <td className="whitespace-nowrap px-4 py-3 text-ink-secondary">{formatDateTime(entry.created_at)}</td>
                    <td className="whitespace-nowrap px-4 py-3">{userLabel(entry.user)}</td>
                    <td className="whitespace-nowrap px-4 py-3">{labelFor(AUDIT_ACTION_CHOICES, entry.action)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-secondary">{entry.ip_address || "—"}</td>
                    <td className="px-4 py-3 text-ink-secondary">{describeDetails(entry.action, entry.details)}</td>
                  </tr>
                ))}
              {!loading && entries.length === 0 && !error && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-ink-secondary">
                    Aucune entrée
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-ink-secondary">
                    Chargement...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {!loading && count > 0 && <Pagination page={page} pageSize={PAGE_SIZE} count={count} onPageChange={setPage} />}
      </div>
    </Layout>
  );
}
