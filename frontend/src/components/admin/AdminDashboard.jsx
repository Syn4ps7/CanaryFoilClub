import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Euro, CalendarDays, Waves, Handshake, LogOut, RefreshCw, Clock } from "lucide-react";
import { adminApi, eur, formatApiError } from "@/lib/adminApi";
import KpiCard from "@/components/admin/KpiCard";
import RevenueSplit from "@/components/admin/RevenueSplit";
import BookingsTable from "@/components/admin/BookingsTable";

const AdminDashboard = ({ admin, onLogout }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await adminApi.get("/admin/stats");
      setStats(data);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const update = async (id, patch) => {
    setBusyId(id);
    try {
      await adminApi.patch(`/admin/bookings/${id}`, patch);
      toast.success("Réservation mise à jour");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const s = stats;
  const today = new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="min-h-screen bg-abyss noise-overlay text-white" data-testid="admin-dashboard">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-abyss/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 sm:px-8 py-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Dashboard</p>
            <h1 className="font-syne text-lg sm:text-xl font-extrabold tracking-tight">
              Canary <span className="text-glow">Foil</span> Club
            </h1>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden sm:inline text-xs text-slate-400" data-testid="admin-email">{admin.email}</span>
            <button
              data-testid="admin-refresh"
              onClick={load}
              className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"
              title="Actualiser"
            >
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
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
      </header>

      <main className="mx-auto max-w-7xl px-5 sm:px-8 py-8 sm:py-10 space-y-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500 capitalize">{today}</p>
            <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Vue d'ensemble</h2>
          </div>
          {s && (
            <p className="text-xs text-slate-400" data-testid="pending-count">
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-amber-300">
                <Clock size={12} /> {s.pending} demande{s.pending > 1 ? "s" : ""} en attente
              </span>
            </p>
          )}
        </div>

        {!s ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-36 rounded-2xl border border-white/5 bg-panel/40 animate-pulse" />)}
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard testId="kpi-revenue-today" label="CA du jour" value={eur(s.revenue.today)} sub={`${s.sessions.today} session${s.sessions.today > 1 ? "s" : ""} aujourd'hui`} icon={Euro} delay={0} />
              <KpiCard testId="kpi-revenue-month" label="CA du mois" value={eur(s.revenue.month)} sub={`${s.sessions.month} session${s.sessions.month > 1 ? "s" : ""} ce mois`} icon={CalendarDays} delay={0.06} />
              <KpiCard testId="kpi-revenue-total" label="CA total" value={eur(s.revenue.total)} sub={`${s.sessions.total} session${s.sessions.total > 1 ? "s" : ""} confirmées · ${s.total_bookings} demandes`} icon={Euro} delay={0.12} />
              <KpiCard testId="kpi-commissions" label="Commissions partenaires" value={eur(s.commissions)} sub={`${Math.round(s.commission_rate * 100)} % sur les réservations apportées`} icon={Handshake} accent="gold" delay={0.18} />
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                <KpiCard
                  testId="kpi-occupancy-today"
                  label="Taux d'occupation — jour"
                  value={`${s.occupancy.today} %`}
                  sub={`${s.occupancy.boards} planches × ${s.occupancy.slots_per_day} créneaux = ${s.occupancy.boards * s.occupancy.slots_per_day} slots/jour`}
                  icon={Waves}
                  delay={0.2}
                />
                <KpiCard testId="kpi-occupancy-month" label="Taux d'occupation — mois" value={`${s.occupancy.month} %`} sub="Moyenne sur les jours du mois en cours" icon={Waves} delay={0.24} />
              </div>
              <div className="lg:col-span-2">
                <RevenueSplit byOffer={s.by_offer} />
              </div>
            </div>

            <BookingsTable bookings={s.recent} onUpdate={update} busyId={busyId} />
          </>
        )}
      </main>
    </div>
  );
};

export default AdminDashboard;
