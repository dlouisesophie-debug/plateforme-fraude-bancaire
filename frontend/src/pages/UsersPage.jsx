import { useEffect, useState } from "react";
import api from "../services/api";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";
import Notice from "../components/Notice";
import { useAuth } from "../hooks/useAuth";
import { ROLE_CHOICES, labelFor } from "../constants/choices";
import { CARD_CLASS, INPUT_CLASS, LABEL_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from "../constants/ui";
import { apiErrorMessage, asList } from "../utils/format";

const EMPTY_USER = { username: "", first_name: "", last_name: "", email: "", role: "agent", password: "" };

const SMALL_BUTTON =
  "rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50";

function CreateUserForm({ onCreated, onCancel }) {
  const [form, setForm] = useState(EMPTY_USER);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { data } = await api.post("/auth/users/", form);
      onCreated(data);
    } catch (err) {
      setError(apiErrorMessage(err, "Création de l'utilisateur impossible."));
    } finally {
      setSubmitting(false);
    }
  }

  const input = (name, label, props = {}) => (
    <div>
      <label htmlFor={`user-${name}`} className={LABEL_CLASS}>
        {label}
      </label>
      <input id={`user-${name}`} name={name} value={form[name]} onChange={handleChange} className={INPUT_CLASS} {...props} />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className={`${CARD_CLASS} mt-6`}>
      <h2 className="text-sm font-medium text-ink-primary">Nouvel utilisateur</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {input("username", "Nom d'utilisateur", { required: true, autoComplete: "off" })}
        {input("first_name", "Prénom")}
        {input("last_name", "Nom")}
        {input("email", "E-mail", { type: "email" })}
        <div>
          <label htmlFor="user-role" className={LABEL_CLASS}>
            Rôle
          </label>
          <select id="user-role" name="role" value={form.role} onChange={handleChange} className={INPUT_CLASS}>
            {ROLE_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        {input("password", "Mot de passe (8 caractères min.)", { type: "password", minLength: 8, required: true, autoComplete: "new-password" })}
      </div>
      <Notice className="mt-4">{error}</Notice>
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={submitting} className={PRIMARY_BUTTON}>
          {submitting ? "Création..." : "Créer"}
        </button>
        <button type="button" onClick={onCancel} className={SECONDARY_BUTTON}>
          Annuler
        </button>
      </div>
    </form>
  );
}

// EF-02 : cette route ne permet pas de changer le mot de passe (pas de champ ici).
function EditUserForm({ user, isSelf, onSaved, onCancel }) {
  const [form, setForm] = useState({
    username: user.username || "",
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    email: user.email || "",
    role: user.role,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const changes = {};
    Object.entries(form).forEach(([key, value]) => {
      if (value !== (user[key] ?? "")) changes[key] = value;
    });
    if (Object.keys(changes).length === 0) {
      onCancel();
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const { data } = await api.patch(`/auth/users/${user.id}/`, changes);
      onSaved({ ...user, ...changes, ...data });
    } catch (err) {
      setError(apiErrorMessage(err, "Modification impossible."));
    } finally {
      setSubmitting(false);
    }
  }

  const input = (name, label, props = {}) => (
    <div>
      <label htmlFor={`edit-${name}`} className={LABEL_CLASS}>
        {label}
      </label>
      <input id={`edit-${name}`} name={name} value={form[name]} onChange={handleChange} className={INPUT_CLASS} {...props} />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className={`${CARD_CLASS} mt-6`}>
      <h2 className="text-sm font-medium text-ink-primary">Modifier « {user.username} »</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {input("username", "Nom d'utilisateur", { required: true, autoComplete: "off" })}
        {input("first_name", "Prénom")}
        {input("last_name", "Nom")}
        {input("email", "E-mail", { type: "email" })}
        <div>
          <label htmlFor="edit-role" className={LABEL_CLASS}>
            Rôle
          </label>
          <select id="edit-role" name="role" value={form.role} onChange={handleChange} disabled={isSelf} className={INPUT_CLASS}>
            {ROLE_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          {isSelf && <p className="mt-1 text-xs text-ink-secondary">Vous ne pouvez pas modifier votre propre rôle.</p>}
        </div>
      </div>
      <Notice className="mt-4">{error}</Notice>
      <div className="mt-4 flex gap-2">
        <button type="submit" disabled={submitting} className={PRIMARY_BUTTON}>
          {submitting ? "Enregistrement..." : "Enregistrer"}
        </button>
        <button type="button" onClick={onCancel} disabled={submitting} className={SECONDARY_BUTTON}>
          Annuler
        </button>
      </div>
    </form>
  );
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [notice, setNotice] = useState(null);
  const [togglingId, setTogglingId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/auth/users/")
      .then((res) => {
        if (!cancelled) setUsers(asList(res.data));
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger les utilisateurs.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleCreated(user) {
    setUsers((prev) => [...prev, { is_active: true, ...user }]);
    setShowForm(false);
    setNotice(`Utilisateur « ${user.username} » créé.`);
  }

  function handleSaved(updated) {
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    setEditingUser(null);
    setNotice(`Utilisateur « ${updated.username} » modifié.`);
  }

  async function handleToggleActive(targetUser) {
    setTogglingId(targetUser.id);
    setError(null);
    try {
      const { data } = await api.patch(`/auth/users/${targetUser.id}/`, { is_active: !targetUser.is_active });
      const updated = { ...targetUser, ...data };
      setUsers((prev) => prev.map((u) => (u.id === targetUser.id ? updated : u)));
      setNotice(`Utilisateur « ${targetUser.username} » ${updated.is_active ? "réactivé" : "désactivé"}.`);
    } catch (err) {
      setError(apiErrorMessage(err, "Action impossible."));
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete(targetUser) {
    setDeletingId(targetUser.id);
    setError(null);
    try {
      await api.delete(`/auth/users/${targetUser.id}/`);
      setUsers((prev) => prev.filter((u) => u.id !== targetUser.id));
      setNotice(`Utilisateur « ${targetUser.username} » supprimé.`);
    } catch (err) {
      setError(apiErrorMessage(err, "Suppression impossible."));
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  }

  return (
    <Layout>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold text-ink-primary">Utilisateurs</h1>
        {!showForm && !editingUser && (
          <button
            type="button"
            onClick={() => {
              setShowForm(true);
              setNotice(null);
            }}
            className={PRIMARY_BUTTON}
          >
            Ajouter un utilisateur
          </button>
        )}
      </div>

      {showForm && (
        <CreateUserForm
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}
      {editingUser && (
        <EditUserForm
          user={editingUser}
          isSelf={editingUser.id === currentUser?.id}
          onSaved={handleSaved}
          onCancel={() => setEditingUser(null)}
        />
      )}
      <Notice tone="success" className="mt-4">{notice}</Notice>
      <Notice className="mt-4">{error}</Notice>

      <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas text-xs font-medium uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-3">Utilisateur</th>
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">E-mail</th>
                <th className="px-4 py-3">Rôle</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => {
                const isSelf = u.id === currentUser?.id;
                return (
                  <tr key={u.id} className="text-ink-primary">
                    <td className="whitespace-nowrap px-4 py-3 font-medium">{u.username}</td>
                    <td className="whitespace-nowrap px-4 py-3">{[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-secondary">{u.email || "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3">{u.role_label || labelFor(ROLE_CHOICES, u.role) || "—"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge value={u.is_active ? "legitimate" : "rejected"} label={u.is_active ? "Actif" : "Inactif"} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {confirmDeleteId === u.id ? (
                        <span className="inline-flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleDelete(u)}
                            disabled={deletingId === u.id}
                            className="rounded-xl bg-danger px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {deletingId === u.id ? "Suppression..." : "Confirmer la suppression"}
                          </button>
                          <button type="button" onClick={() => setConfirmDeleteId(null)} disabled={deletingId === u.id} className={SMALL_BUTTON}>
                            Annuler
                          </button>
                        </span>
                      ) : (
                        <span className="inline-flex gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingUser(u);
                              setShowForm(false);
                              setNotice(null);
                            }}
                            className={SMALL_BUTTON}
                          >
                            Modifier
                          </button>
                          {!isSelf && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleToggleActive(u)}
                                disabled={togglingId === u.id}
                                className={SMALL_BUTTON}
                              >
                                {togglingId === u.id ? "..." : u.is_active ? "Désactiver" : "Réactiver"}
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirmDeleteId(u.id)}
                                className="rounded-xl border border-line px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger-soft"
                              >
                                Supprimer
                              </button>
                            </>
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!loading && users.length === 0 && !error && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-ink-secondary">
                    Aucun utilisateur
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-ink-secondary">
                    Chargement...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
