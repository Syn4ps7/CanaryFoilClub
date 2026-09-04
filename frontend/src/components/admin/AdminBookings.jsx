import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Search, Download, X } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";
import BookingsTable, { STATUS_META } from "@/components/admin/BookingsTable";

const inputCls =
  "rounded-xl border border-white/15 bg-deep px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const EMPTY = { q: "", status: "", date_from: "", date_to: "" };

const AdminBookings = ({ onLogout }) => {
  const [filters, setFilters] = useState(EMPTY);
  const [bookings, setBookings] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data }, { data: cfg }] = await Promise.all([
        adminApi.get("/admin/bookings", { params }),
        adminApi.get("/admin/settings"),
      ]);
      setBookings(data);
      setSettings(cfg);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.q, filters.status, filters.date_from, filters.date_to, onLogout]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));

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

  const exportCsv = async () => {
    try {
      const res = await adminApi.get("/admin/bookings/export.csv", { params, responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `canary-foil-club-reservations-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Export CSV téléchargé");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const total = bookings.reduce((a, b) => a + (["confirmed", "completed"].includes(b.status) ? b.amount : 0), 0);
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="space-y-6" data-testid="admin-bookings-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Comptabilité</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Toutes les réservations</h2>
        </div>
        <button
          data-testid="bookings-export-csv"
          onClick={exportCsv}
          className="inline-flex items-center gap-2 rounded-full bg-glow px-5 py-2.5 font-syne text-xs font-bold text-abyss btn-glow"
        >
          <Download size={14} /> Export CSV
        </button>
      </div>

      <div className="rounded-2xl border border-white/10 bg-panel/70 p-4 sm:p-5 backdrop-blur-xl" data-testid="bookings-filters">
        <div className="grid gap-3 md:grid-cols-[1fr_180px_170px_170px_auto]">
          <div className="relative">
            <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input data-testid="bookings-search" value={filters.q} onChange={set("q")} className={`${inputCls} w-full pl-10`} placeholder="Nom, email, téléphone, hôtel, partenaire…" />
          </div>
          <select data-testid="bookings-filter-status" value={filters.status} onChange={set("status")} className={inputCls} style={{ backgroundColor: "#0A1322" }}>
            <option value="">Tous les statuts</option>
            {Object.entries(STATUS_META).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <input data-testid="bookings-filter-from" type="date" value={filters.date_from} onChange={set("date_from")} className={inputCls} title="Session du" />
          <input data-testid="bookings-filter-to" type="date" value={filters.date_to} onChange={set("date_to")} className={inputCls} title="Session au" />
          <button
            data-testid="bookings-filters-reset"
            onClick={() => setFilters(EMPTY)}
            disabled={!hasFilters}
            className="inline-flex items-center justify-center gap-1 rounded-xl border border-white/15 px-4 py-2.5 text-xs text-slate-300 transition-colors hover:border-white/40 disabled:opacity-40"
          >
            <X size={13} /> Effacer
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-500" data-testid="bookings-summary">
          {loading ? "Chargement…" : <>{bookings.length} réservation{bookings.length > 1 ? "s" : ""} · CA encaissable <span className="text-white font-medium">{new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(total)}</span> (confirmées + réalisées)</>}
        </p>
      </div>

      <BookingsTable bookings={bookings} onUpdate={update} busyId={busyId} title="Résultats" slotsPerDay={settings?.slots_per_day} />
    </div>
  );
};

export default AdminBookings;
