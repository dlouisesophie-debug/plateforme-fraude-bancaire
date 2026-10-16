// Pages accessibles par rôle (CDC 5.1). L'admin voit tout.
export const NAV_ITEMS = [
  { to: "/", label: "Dashboard", roles: ["admin", "analyst", "agent"] },
  { to: "/transactions", label: "Transactions", roles: ["admin", "analyst", "agent"] },
  { to: "/transactions/new", label: "Nouvelle transaction", roles: ["admin", "agent"] },
  { to: "/alerts", label: "Alertes", roles: ["admin", "analyst"] },
  { to: "/reports", label: "Rapports", roles: ["admin", "agent"] },
  { to: "/users", label: "Utilisateurs", roles: ["admin"] },
  { to: "/model", label: "Modèle IA", roles: ["admin"] },
];

// Un superutilisateur Django sans rôle métier est traité comme un admin,
// comme le fait la permission IsAdmin côté backend.
export function effectiveRole(user) {
  if (!user) return null;
  if (user.is_superuser) return "admin";
  return user.role || null;
}

export function canAccess(user, roles) {
  const role = effectiveRole(user);
  return Boolean(role && roles.includes(role));
}
