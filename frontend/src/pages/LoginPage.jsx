import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError("Identifiants invalides");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="flex-[1.1] bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800 text-ink-inverse p-14 px-16 flex flex-col justify-between">
        <div className="flex items-center gap-3">
          <div className="w-[38px] h-[38px] rounded-[10px] bg-brand flex items-center justify-center">
            <i className="ti ti-shield-check text-white text-xl" />
          </div>
          <span className="font-display text-[19px] font-semibold">FraudGuard</span>
        </div>

        <div>
          <div className="text-xs tracking-[0.14em] uppercase text-[#8FA6D1] mb-4">
            Plateforme de détection de fraude
          </div>
          <h1 className="font-display text-[40px] font-medium leading-[1.18] tracking-tight max-w-[420px]">
            Chaque transaction, vérifiée avant qu'elle ne coûte cher.
          </h1>
          <p className="mt-4 text-[#B7C6E6] text-[15px] leading-relaxed max-w-[420px]">
            Scoring en temps quasi-réel, alertes priorisées et traçabilité complète pour vos équipes de conformité.
          </p>
        </div>

        <div className="flex gap-9">
          <div>
            <div className="font-display text-[28px] font-medium">98.2%</div>
            <div className="text-xs text-[#8FA6D1] mt-1">Recall sur classe fraude</div>
          </div>
          <div>
            <div className="font-display text-[28px] font-medium">&lt;500ms</div>
            <div className="text-xs text-[#8FA6D1] mt-1">Temps de scoring</div>
          </div>
          <div>
            <div className="font-display text-[28px] font-medium">24/7</div>
            <div className="text-xs text-[#8FA6D1] mt-1">Surveillance active</div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-10">
        <form className="w-full max-w-[360px]" onSubmit={handleSubmit}>
          <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary mb-2">
            Espace sécurisé
          </div>
          <h2 className="font-display text-[26px] font-semibold mb-1.5">Connexion</h2>
          <p className="text-ink-secondary text-sm mb-8">
            Accédez à votre tableau de bord FraudGuard
          </p>

          <div className="mb-4">
            <label className="block text-[13px] font-medium mb-1.5">Nom d'utilisateur</label>
            <div className="relative">
              <i className="ti ti-user absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-secondary" />
              <input
                className="w-full pl-10 pr-3.5 py-3 border border-line rounded-[10px] text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="prenom.nom"
              />
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-[13px] font-medium mb-1.5">Mot de passe</label>
            <div className="relative">
              <i className="ti ti-lock absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-secondary" />
              <input
                type="password"
                className="w-full pl-10 pr-3.5 py-3 border border-line rounded-[10px] text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
              />
            </div>
          </div>

          {error && <div className="text-danger text-[13px] mb-4">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-[10px] bg-brand text-white text-sm font-semibold disabled:opacity-60"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>

          <div className="mt-7 p-3.5 px-4 bg-brand-soft rounded-[10px] text-[12.5px] text-[#2B4C8C] leading-relaxed">
            Mode démo actif — identifiants factices acceptés tant que{" "}
            <code>REACT_APP_USE_MOCKS=true</code>.
          </div>
        </form>
      </div>
    </div>
  );
}
