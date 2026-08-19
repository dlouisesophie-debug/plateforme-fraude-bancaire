import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const styles = {
  screen: { display: "flex", minHeight: "100vh" },
  brandPanel: {
    flex: 1.1,
    background: "linear-gradient(160deg, var(--navy-950) 0%, var(--navy-900) 55%, var(--navy-800) 100%)",
    color: "var(--text-inverse)",
    padding: "56px 64px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  brandMark: { display: "flex", alignItems: "center", gap: 12 },
  logo: { width: 38, height: 38, borderRadius: 10, background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center" },
  h1: { fontFamily: "var(--font-display)", fontSize: 40, fontWeight: 500, lineHeight: 1.18, letterSpacing: "-0.01em", maxWidth: 420 },
  formPanel: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 },
  formCard: { width: "100%", maxWidth: 360 },
  field: { marginBottom: 18 },
  label: { display: "block", fontSize: 13, fontWeight: 500, marginBottom: 7 },
  input: { width: "100%", padding: "12px 14px", border: "1px solid var(--border)", borderRadius: 10, fontSize: 14 },
  btn: { width: "100%", padding: 13, border: "none", borderRadius: 10, background: "var(--brand)", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer" },
};

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
    <div style={styles.screen}>
      <div style={styles.brandPanel}>
        <div style={styles.brandMark}>
          <div style={styles.logo}><i className="ti ti-shield-check" style={{ color: "#fff", fontSize: 20 }} /></div>
          <span style={{ fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 600 }}>FraudGuard</span>
        </div>
        <div>
          <div style={{ fontSize: 12, letterSpacing: "0.14em", textTransform: "uppercase", color: "#8FA6D1", marginBottom: 18 }}>
            Plateforme de détection de fraude
          </div>
          <h1 style={styles.h1}>Chaque transaction, vérifiée avant qu'elle ne coûte cher.</h1>
        </div>
        <div style={{ display: "flex", gap: 36 }}>
          <div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 500 }}>98.2%</div>
            <div style={{ fontSize: 12, color: "#8FA6D1", marginTop: 4 }}>Recall sur classe fraude</div>
          </div>
        </div>
      </div>

      <div style={styles.formPanel}>
        <form style={styles.formCard} onSubmit={handleSubmit}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-secondary)", marginBottom: 8 }}>
            Espace sécurisé
          </div>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 600, marginBottom: 6 }}>Connexion</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 32 }}>
            Accédez à votre tableau de bord FraudGuard
          </p>

          <div style={styles.field}>
            <label style={styles.label}>Nom d'utilisateur</label>
            <input style={styles.input} value={username} onChange={(e) => setUsername(e.target.value)} placeholder="prenom.nom" />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Mot de passe</label>
            <input style={styles.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••" />
          </div>

          {error && <div style={{ color: "var(--danger)", fontSize: 13, marginBottom: 16 }}>{error}</div>}

          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>

          <div style={{ marginTop: 28, padding: "14px 16px", background: "var(--brand-soft)", borderRadius: 10, fontSize: 12.5, color: "#2B4C8C", lineHeight: 1.55 }}>
            Mode démo actif — identifiants factices acceptés tant que <code>REACT_APP_USE_MOCKS=true</code>.
          </div>
        </form>
      </div>
    </div>
  );
}
