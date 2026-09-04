import { useState } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListOrdered, CalendarRange, LogOut, KeyRound, Star, Gift } from "lucide-react";
import ChangePassword from "@/components/admin/ChangePassword";

const NAV = [
  { to: "/admin", label: "Vue d'ensemble", icon: LayoutDashboard, end: true, id: "nav-dashboard" },
  { to: "/admin/bookings", label: "Réservations", icon: ListOrdered, id: "nav-bookings" },
  { to: "/admin/planning", label: "Planning", icon: CalendarRange, id: "nav-planning" },
  { to: "/admin/reviews", label: "Avis", icon: Star, id: "nav-reviews" },
  { to: "/admin/vouchers", label: "Bons cadeaux", icon: Gift, id: "nav-vouchers" },
];

const AdminLayout = ({ admin, onLogout, children }) => {
  const [pwOpen, setPwOpen] = useState(false);
  return (
  <div className="min-h-screen bg-abyss noise-overlay text-white" data-testid="admin-shell">
    <header className="sticky top-0 z-20 border-b border-white/10 bg-abyss/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 sm:px-8 py-3.5">
        <div className="flex items-center gap-6 sm:gap-10">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Admin</p>
            <h1 className="font-syne text-lg font-extrabold tracking-tight leading-none">
              Canary <span className="text-glow">Foil</span> Club
            </h1>
          </div>
          <nav className="hidden md:flex items-center gap-1" data-testid="admin-nav">
            {NAV.map(({ to, label, icon: Icon, end, id }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                data-testid={id}
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition-colors ${
                    isActive ? "bg-glow/10 text-glow border border-glow/30" : "text-slate-400 border border-transparent hover:text-white hover:bg-white/5"
                  }`
                }
              >
                <Icon size={14} /> {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline text-xs text-slate-400" data-testid="admin-email">{admin.email}</span>
          <button
            data-testid="admin-change-password"
            onClick={() => setPwOpen(true)}
            title="Changer le mot de passe"
            className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"
          >
            <KeyRound size={14} />
          </button>
          <button
            data-testid="admin-logout"
            onClick={onLogout}
            className="inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-xs text-slate-300 transition-colors hover:border-red-400/60 hover:text-red-300"
          >
            <LogOut size={14} /> <span className="hidden sm:inline">Déconnexion</span>
          </button>
        </div>
      </div>
      <nav className="md:hidden flex border-t border-white/10" data-testid="admin-nav-mobile">
        {NAV.map(({ to, label, icon: Icon, end, id }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            data-testid={`${id}-mobile`}
            className={({ isActive }) =>
              `flex-1 inline-flex items-center justify-center gap-1.5 py-2.5 text-[11px] transition-colors ${isActive ? "text-glow border-b-2 border-glow" : "text-slate-400"}`
            }
          >
            <Icon size={13} /> {label}
          </NavLink>
        ))}
      </nav>
    </header>
    <main className="mx-auto max-w-7xl px-5 sm:px-8 py-8 sm:py-10 space-y-8">{children}</main>
    <ChangePassword open={pwOpen} onClose={() => setPwOpen(false)} />
  </div>
  );
};

export default AdminLayout;
