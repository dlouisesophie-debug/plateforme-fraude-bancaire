import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import api, { mockApi, USE_MOCKS_FLAG } from "../services/api";
import { mockUser } from "../mocks/mockData";

const ROLE_LABELS = { admin: "Administrateur", analyst: "Analyste Fraude", agent: "Agent Financier" };
const ROLE_CLASSES = {
  admin: "bg-danger-soft text-danger",
  analyst: "bg-brand-soft text-brand",
  agent: "bg-success-soft text-success",
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user] = useState(mockUser);

  useEffect(() => {
    async function load() {
      const data = USE_MOCKS_FLAG ? await mockApi.getUsers() : (await api.get("/auth/users/")).data;
      setUsers(data.results || []);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="flex">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title="Utilisateurs">
          <button className="flex items-center gap-1.5 px-4 py-2.5 rounded-[9px] bg-brand text-white text-[13px] font-semibold">
            <i className="ti ti-user-plus" /> Créer un utilisateur
          </button>
        </Topbar>

        <div className="p-7">
          <div className="text-ink-secondary text-[13.5px] mb-5">
            Gestion des comptes et des rôles — réservé aux administrateurs.
          </div>

          <div className="bg-surface border border-line rounded-xl overflow-hidden">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="bg-canvas">
                  {["Utilisateur", "Email", "Rôle", "Statut", ""].map((h) => (
                    <th key={h} className="text-left px-5 py-3.5 text-[11px] uppercase tracking-wide text-ink-secondary border-b border-line">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={5} className="p-5 text-ink-secondary">Chargement...</td></tr>
                )}
                {!loading && users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-5 py-3.5 border-b border-line">
                      <div className="flex items-center gap-2.5">
                        <div className="w-[30px] h-[30px] rounded-full bg-brand text-white flex items-center justify-center text-[11px] font-semibold">
                          {u.first_name[0]}{u.last_name[0]}
                        </div>
                        <div className="font-semibold">{u.first_name} {u.last_name}</div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 border-b border-line text-ink-secondary">{u.email}</td>
                    <td className="px-5 py-3.5 border-b border-line">
                      <span className={`text-[11.5px] font-semibold px-2.5 py-1 rounded-full ${ROLE_CLASSES[u.role] || ROLE_CLASSES.agent}`}>
                        {ROLE_LABELS[u.role] || u.role}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 border-b border-line">
                      <span className={`text-[11.5px] font-semibold px-2.5 py-1 rounded-full ${u.is_active ? "bg-success-soft text-success" : "bg-canvas text-ink-secondary"}`}>
                        {u.is_active ? "Actif" : "Désactivé"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 border-b border-line">
                      <i className="ti ti-dots-vertical text-ink-secondary cursor-pointer" />
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
