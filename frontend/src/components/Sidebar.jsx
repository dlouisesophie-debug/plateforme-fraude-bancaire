import { NavLink } from "react-router-dom";

const navItems = [
  { section: "Principal", items: [
    { to: "/", icon: "ti-layout-dashboard", label: "Dashboard" },
    { to: "/transactions", icon: "ti-list-details", label: "Transactions" },
    { to: "/alerts", icon: "ti-alert-triangle", label: "Alertes", badge: 7 },
  ]},
  { section: "Analyse", items: [
    { to: "/reports", icon: "ti-file-report", label: "Rapports" },
    { to: "/ml-models", icon: "ti-brain", label: "Modèles ML" },
  ]},
];

const styles = {
  sidebar: { width: 232, background: "var(--navy-950)", color: "var(--text-inverse)", display: "flex", flexDirection: "column", flexShrink: 0, minHeight: "100vh" },
  brand: { padding: "22px 20px 18px", display: "flex", alignItems: "center", gap: 10, borderBottom: "1px solid rgba(255,255,255,0.08)" },
  logo: { width: 32, height: 32, borderRadius: 8, background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center" },
  brandName: { fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 600 },
  navGroup: { padding: "16px 12px", flex: 1 },
  navLabel: { fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6E84AD", padding: "0 10px", margin: "14px 0 6px" },
  navItem: { display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: 8, fontSize: 13.5, color: "#B9C6E3", textDecoration: "none", marginBottom: 2 },
  navItemActive: { background: "rgba(47,111,237,0.18)", color: "#fff", fontWeight: 500 },
  badge: { marginLeft: "auto", background: "var(--danger)", color: "#fff", fontSize: 10, padding: "1px 7px", borderRadius: 9 },
  userBox: { padding: 14, borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", gap: 10 },
  avatar: { width: 30, height: 30, borderRadius: "50%", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600, color: "#fff" },
};

export default function Sidebar({ user }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.brand}>
        <div style={styles.logo}><i className="ti ti-shield-check" style={{ color: "#fff", fontSize: 16 }} /></div>
        <span style={styles.brandName}>FraudGuard</span>
      </div>

      <nav style={styles.navGroup}>
        {navItems.map((group) => (
          <div key={group.section}>
            <div style={styles.navLabel}>{group.section}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                style={({ isActive }) => ({ ...styles.navItem, ...(isActive ? styles.navItemActive : {}) })}
              >
                <i className={`ti ${item.icon}`} style={{ fontSize: 17, opacity: 0.9 }} />
                {item.label}
                {item.badge && <span style={styles.badge}>{item.badge}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div style={styles.userBox}>
        <div style={styles.avatar}>
          {user ? `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}` : "?"}
        </div>
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 500 }}>
            {user ? `${user.first_name} ${user.last_name}` : "Chargement..."}
          </div>
          <div style={{ fontSize: 11, color: "#8FA6D1" }}>
            {user?.role === "admin" && "Administrateur"}
            {user?.role === "analyst" && "Analyste Fraude"}
            {user?.role === "agent" && "Agent Financier"}
          </div>
        </div>
      </div>
    </aside>
  );
}
