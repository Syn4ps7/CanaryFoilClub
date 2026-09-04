import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Euro, CalendarDays, Waves, Handshake, RefreshCw, Clock } from "lucide-react";
import { adminApi, eur, formatApiError } from "@/lib/adminApi";
import KpiCard from "@/components/admin/KpiCard";
import RevenueSplit from "@/components/admin/RevenueSplit";
import BookingsTable from "@/components/admin/BookingsTable";
import CapacitySettings from "@/components/admin/CapacitySettings";
import WeeklyReportCard from "@/components/admin/WeeklyReportCard";
import StatusBreakdown from "@/components/admin/StatusBreakdown";

const AdminDashboard = ({ onLogout }) => {
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data }, { data: cfg }] = await Promise.all([adminApi.get("/admin/stats"), adminApi.get("/admin/settings")]);
      setStats(data);
      setSettings(cfg);
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
      toast.success(patch.status === "confirmed" ? "Réservation confirmée — email envoyé au client" : "Réservation mise à jour");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const sendReviewRequest = async (id) => {
    setBusyId(id);
    try {
      await adminApi.post(`/admin/bookings/${id}/review-request`);
      toast.success("Demande d'avis envoyée au client");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const sendReminder = async (id) => {
    setBusyId(id);
    try {
      await adminApi.post(`/admin/bookings/${id}/reminder`);
      toast.success("Rappel envoyé au client avec le point de rendez-vous");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const s = stats;
  const today = new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
  const plural = (n, w) => `${n} ${w}${n > 1 ? "s" : ""}`;

  return (
    <div className="space-y-8" data-testid="admin-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500 capitalize">{today}</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Vue d'ensemble</h2>
        </div>
        <div className="flex items-center gap-2">
          {s && (
            <span data-testid="pending-count" className="inline-flex items-center gap-1 rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-xs text-amber-300">
              <Clock size={12} /> {plural(s.pending, "demande")} en attente
            </span>
          )}
          <button
            data-testid="admin-refresh"
            onClick={load}
            className="grid h-8 w-8 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"
            title="Actualiser"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {!s ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-36 rounded-2xl border border-white/5 bg-panel/40 animate-pulse" />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard testId="kpi-revenue-today" label="CA encaissé aujourd'hui" value={eur(s.revenue.today)} sub={`${plural(s.confirmations.today, "réservation")} confirmée${s.confirmations.today > 1 ? "s" : ""} aujourd'hui · ${plural(s.sessions.today, "session")} au planning`} icon={Euro} delay={0} />
            <KpiCard testId="kpi-revenue-month" label="CA encaissé ce mois" value={eur(s.revenue.month)} sub={`${plural(s.confirmations.month, "réservation")} confirmée${s.confirmations.month > 1 ? "s" : ""} ce mois · ${plural(s.sessions.month, "session")} au planning`} icon={CalendarDays} delay={0.06} />
            <KpiCard testId="kpi-revenue-total" label="CA total" value={eur(s.revenue.total)} sub={`${plural(s.sessions.total, "session")} confirmées ou réalisées · ${s.total_bookings} demandes`} icon={Euro} delay={0.12} />
            <KpiCard testId="kpi-commissions" label="Commissions partenaires" value={eur(s.commissions)} sub={`${Math.round(s.commission_rate * 100)} % sur les réservations apportées`} icon={Handshake} accent="gold" delay={0.18} />
          </div>

          <StatusBreakdown stats={s} />

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
              <KpiCard
                testId="kpi-occupancy-today"
                label="Taux d'occupation — jour"
                value={`${s.occupancy.today} %`}
                sub={`${s.occupancy.used_today} / ${s.occupancy.capacity} sessions-planche (${s.occupancy.boards} planches × ${s.occupancy.slots_per_day} créneaux)`}
                icon={Waves}
                delay={0.2}
              />
              <KpiCard testId="kpi-occupancy-month" label="Taux d'occupation — mois" value={`${s.occupancy.month} %`} sub="Moyenne sur les jours du mois en cours" icon={Waves} delay={0.24} />
              <CapacitySettings settings={settings} onSaved={() => load()} />
            </div>
            <div className="lg:col-span-2 space-y-4">
              <RevenueSplit byOffer={s.by_offer} />
              <WeeklyReportCard />
            </div>
          </div>

          <BookingsTable bookings={s.recent} onUpdate={update} onReminder={sendReminder} onReviewRequest={sendReviewRequest} busyId={busyId} title="10 dernières réservations" allSlotTimes={settings?.slot_times} />
        </>
      )}
    </div>
  );
};

export default AdminDashboard;
