import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, clearToken } from "../api";
import { useUser } from "../auth";
import type { Copro } from "../types";

const NAV = [
  { to: "/", label: "Tableau de bord", icon: "▦" },
  { to: "/lots", label: "Lots & occupants", icon: "⌂" },
  { to: "/comptes", label: "Comptes", icon: "€" },
  { to: "/ag", label: "Assemblées", icon: "🗳" },
  { to: "/documents", label: "Documents", icon: "▤" },
  { to: "/carnet", label: "Carnet d'entretien", icon: "🔧" },
  { to: "/settings", label: "Réglages", icon: "⚙" },
];

export default function Layout() {
  const { user } = useUser();
  const [copro, setCopro] = useState<Copro | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    api.get<Copro>("/copro").then(setCopro).catch(() => {});
  }, []);

  function logout() {
    clearToken();
    nav("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">
            C
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-slate-800">CoproApp</p>
            <p className="truncate text-xs text-slate-500">{copro?.nom ?? "…"}</p>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 py-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
                }`
              }
            >
              <span className="w-5 text-center text-base leading-none">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 px-5 py-3.5">
          <p className="truncate text-sm font-medium text-slate-700">{user?.nom ?? "…"}</p>
          <p className="truncate text-xs text-slate-500">
            {user ? (user.role === "syndic" ? "Syndic bénévole" : "Copropriétaire") : "…"}
          </p>
          <button onClick={logout} className="mt-2 text-xs font-medium text-slate-500 hover:text-red-600">
            Se déconnecter
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
}
