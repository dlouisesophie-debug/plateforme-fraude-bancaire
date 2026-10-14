import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { USE_MOCKS } from "../services/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      if (!err.response) {
        setError("Serveur injoignable. Verifiez que le backend est demarre.");
      } else if (err.response.status === 401) {
        setError("Identifiants invalides");
      } else {
        setError(`Erreur serveur (${err.response.status})`);
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm rounded-xl border border-line bg-surface p-8 shadow-sm">
        <h1 className="font-display text-2xl font-semibold text-ink-primary">FraudGuard</h1>
        <p className="mt-1 text-sm text-ink-secondary">Connexion a votre espace</p>
        {USE_MOCKS && (
          <div className="mt-4 rounded-xl bg-canvas px-3 py-2 text-xs text-ink-secondary">
            Mode demo (sans backend) : n'importe quel nom et mot de passe
          </div>
        )}
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-ink-primary">
              Nom d'utilisateur
            </label>
            <input
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-ink-primary outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand-soft"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-ink-primary">
              Mot de passe
            </label>
            <input
              type="password"
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-ink-primary outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand-soft"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <div className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}
          <button
            type="submit"
            className="w-full rounded-xl bg-brand px-3 py-2 font-medium text-white transition-colors hover:bg-navy-800"
          >
            Se connecter
          </button>
        </form>
      </div>
    </div>
  );
}
