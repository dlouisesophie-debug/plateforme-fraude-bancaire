import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { NAV_ITEMS, canAccess } from "../constants/roles";
import { ROLE_CHOICES, labelFor } from "../constants/choices";
import { displayName } from "../utils/format";
import Logo from "./Logo";

function navLinkClass({ isActive }) {
  return `block whitespace-nowrap rounded-xl px-3 py-2 text-sm font-medium transition-colors xl:px-2.5 xl:py-1.5 ${
    isActive ? "bg-brand text-white" : "text-ink-inverse/80 hover:bg-navy-800 hover:text-ink-inverse"
  }`;
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // Referme le menu mobile après chaque navigation.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Profil inconnu (ex. /auth/me/ indisponible) : seules les pages communes.
  const items = user
    ? NAV_ITEMS.filter((item) => canAccess(user, item.roles))
    : NAV_ITEMS.filter((item) => item.roles.length === 3);
  const roleLabel = user?.role_label || labelFor(ROLE_CHOICES, user?.role) || (user?.is_superuser ? "Administrateur" : "");

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const userBlock = user && (
    <div className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-800 text-sm font-semibold text-ink-inverse"
      >
        {displayName(user).charAt(0).toUpperCase()}
      </span>
      <div className="min-w-0 max-w-[11rem] leading-tight" title={displayName(user)}>
        <p className="truncate text-sm font-medium text-ink-inverse">{displayName(user)}</p>
        {roleLabel && <p className="truncate text-xs text-ink-inverse/60">{roleLabel}</p>}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-navy-950">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Logo variant="dark" />

          <nav className="hidden min-w-0 flex-1 items-center justify-center gap-1 xl:flex">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} end className={navLinkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden shrink-0 items-center gap-3 xl:flex">
            {userBlock}
            <button
              type="button"
              onClick={handleLogout}
              className="whitespace-nowrap rounded-xl px-3 py-1.5 text-sm font-medium text-ink-inverse/80 transition-colors hover:bg-danger hover:text-white"
            >
              Déconnexion
            </button>
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? "Fermer le menu" : "Ouvrir le menu"}
            className="rounded-xl p-2 text-ink-inverse transition-colors hover:bg-navy-800 xl:hidden"
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>

        {menuOpen && (
          <div id="mobile-menu" className="border-t border-navy-800 px-4 pb-4 pt-3 xl:hidden">
            {userBlock && <div className="mb-3">{userBlock}</div>}
            <nav className="space-y-1">
              {items.map((item) => (
                <NavLink key={item.to} to={item.to} end className={navLinkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-3 w-full rounded-xl px-3 py-2 text-left text-sm font-medium text-ink-inverse/80 transition-colors hover:bg-danger hover:text-white"
            >
              Déconnexion
            </button>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
