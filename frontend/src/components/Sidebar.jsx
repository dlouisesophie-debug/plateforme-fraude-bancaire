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
  { section: "Administration", items: [
    { to: "/users", icon: "ti-users-group", label: "Utilisateurs" },
  ]},
];

export default function Sidebar({ user }) {
  return (
    <aside className="w-[232px] shrink-0 min-h-screen bg-navy-950 text-ink-inverse flex flex-col">
      <div className="flex items-center gap-2.5 px-5 py-[22px] pb-[18px] border-b border-white/10">
        <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center">
          <i className="ti ti-shield-check text-white text-base" />
        </div>
        <span className="font-display text-[16px] font-semibold">FraudGuard</span>
      </div>

      <nav className="px-3 py-4 flex-1">
        {navItems.map((group) => (
          <div key={group.section}>
            <div className="text-[10px] tracking-widest uppercase text-[#6E84AD] px-2.5 mt-3.5 mb-1.5">
              {group.section}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13.5px] no-underline mb-0.5 ${
                    isActive ? "bg-brand/20 text-white font-medium" : "text-[#B9C6E3]"
                  }`
                }
              >
                <i className={`ti ${item.icon} text-[17px] opacity-90`} />
                {item.label}
                {item.badge && (
                  <span className="ml-auto bg-danger text-white text-[10px] px-[7px] py-px rounded-full">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="p-3.5 border-t border-white/10 flex items-center gap-2.5">
        <div className="w-[30px] h-[30px] rounded-full bg-brand flex items-center justify-center text-[11px] font-semibold text-white">
          {user ? `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}` : "?"}
        </div>
        <div>
          <div className="text-[12.5px] font-medium">
            {user ? `${user.first_name} ${user.last_name}` : "Chargement..."}
          </div>
          <div className="text-[11px] text-[#8FA6D1]">
            {user?.role === "admin" && "Administrateur"}
            {user?.role === "analyst" && "Analyste Fraude"}
            {user?.role === "agent" && "Agent Financier"}
          </div>
        </div>
      </div>
    </aside>
  );
}
