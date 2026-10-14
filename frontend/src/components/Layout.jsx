import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/alerts", label: "Alertes" },
];

export default function Layout({ children }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-navy-950">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-display text-xl font-semibold text-ink-inverse">
            FraudGuard
          </span>
          <nav className="flex items-center gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-brand text-white"
                      : "text-ink-inverse/80 hover:bg-navy-800 hover:text-ink-inverse"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={handleLogout}
              className="ml-2 rounded-xl px-3 py-1.5 text-sm font-medium text-ink-inverse/80 transition-colors hover:bg-danger hover:text-white"
            >
              Deconnexion
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
