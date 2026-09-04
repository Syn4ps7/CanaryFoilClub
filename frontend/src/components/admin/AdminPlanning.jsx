import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";
import { EXP_LABELS } from "@/components/admin/BookingsTable";
import WeatherCard from "@/components/admin/WeatherCard";
import WeekView from "@/components/admin/WeekView";

const iso = (d) => d.toISOString().slice(0, 10);
const shift = (s, n) => {
  const d = new Date(`${s}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return iso(d);
};

const boardsNeeded = (b, boards) => {
  if (b.experience === "discovery") return Math.min(b.participants, boards);
  if (b.experience === "duo") return Math.min(2, boards);
  if (b.experience === "testdrive") return 1;
  if (b.experience === "corporate") return boards;
  return 0;
};

const cellsForSlot = (slot, boards) => {
  const cells = [];
  slot.bookings.forEach((b) => {
    for (let i = 0; i < boardsNeeded(b, boards); i++) cells.push(b);
  });
  return cells.slice(0, boards);
};

const AdminPlanning = ({ onLogout }) => {
  const [day, setDay] = useState(iso(new Date()));
  const [view, setView] = useState("day");
  const [plan, setPlan] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    if (view !== "day") return;
    try {
      const { data } = await adminApi.get("/admin/planning", { params: { day } });
      setPlan(data);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    }
  }, [day, view, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const assign = async (id, slot) => {
    setBusyId(id);
    try {
      await adminApi.patch(`/admin/bookings/${id}`, { slot });
      toast.success(slot ? `Placée à ${plan?.slot_times?.[slot - 1] || `C${slot}`}` : "Créneau retiré");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const label = new Date(`${day}T12:00:00Z`).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const pct = plan ? Math.round((plan.used / plan.capacity) * 100) : 0;
  const pickDay = (d) => {
    setDay(d);
    setView("day");
  };

  return (
    <div className="space-y-6" data-testid="admin-planning-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Planning</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight capitalize">{view === "day" ? label : "Vue semaine"}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-full border border-white/15 bg-deep p-1" data-testid="planning-view-toggle">
            {[["day", "Jour"], ["week", "Semaine"]].map(([v, l]) => (
              <button
                key={v}
                data-testid={`planning-view-${v}`}
                onClick={() => setView(v)}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${view === v ? "bg-glow text-abyss" : "text-slate-300 hover:text-white"}`}
              >
                {l}
              </button>
            ))}
          </div>
          {view === "day" && (
            <>
          <button data-testid="planning-prev-day" onClick={() => setDay((d) => shift(d, -1))} className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"><ChevronLeft size={16} /></button>
          <div className="relative">
            <CalendarDays size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input data-testid="planning-date" type="date" value={day} onChange={(e) => e.target.value && setDay(e.target.value)} className="rounded-full border border-white/15 bg-deep pl-9 pr-4 py-2 text-sm text-white outline-none focus:border-glow/70" />
          </div>
          <button data-testid="planning-next-day" onClick={() => setDay((d) => shift(d, 1))} className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"><ChevronRight size={16} /></button>
          <button data-testid="planning-today" onClick={() => setDay(iso(new Date()))} className="rounded-full border border-white/15 px-4 py-2 text-xs text-slate-300 transition-colors hover:border-glow/60 hover:text-glow">Aujourd'hui</button>
            </>
          )}
        </div>
      </div>

      {view === "week" && <WeekView anchor={day} today={iso(new Date())} onPickDay={pickDay} onLogout={onLogout} />}

      {view === "day" && <WeatherCard day={day} />}

      {view === "day" && plan && (
        <>
          <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-white/10 bg-panel/70 px-5 py-4 backdrop-blur-xl" data-testid="planning-summary">
            <p className="font-outfit text-2xl font-semibold tabular-nums">{pct} %</p>
            <div className="flex-1 min-w-[160px]">
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} className="h-full rounded-full bg-glow" style={{ boxShadow: "0 0 12px rgba(0,240,255,0.5)" }} />
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                {plan.used} / {plan.capacity} sessions-planche occupées · {plan.boards} planches × {plan.slots_per_day} créneaux
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-glow/70" /> B2C</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-gold/80" /> Corporate</span>
              <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm border border-dashed border-white/30" /> Libre</span>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-panel/70 backdrop-blur-xl" data-testid="planning-grid">
            <div className="min-w-[640px]">
              <div className="grid border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500" style={{ gridTemplateColumns: `130px repeat(${plan.boards}, minmax(0,1fr))` }}>
                <div className="px-4 py-3">Créneau</div>
                {[...Array(plan.boards)].map((_, i) => <div key={i} className="px-3 py-3 text-center">Planche {i + 1}</div>)}
              </div>
              {plan.slots.map((s, si) => {
                const cells = cellsForSlot(s, plan.boards);
                return (
                  <motion.div
                    key={s.slot}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: si * 0.05 }}
                    data-testid={`planning-slot-${s.slot}`}
                    className="grid items-stretch border-b border-white/5 last:border-0"
                    style={{ gridTemplateColumns: `130px repeat(${plan.boards}, minmax(0,1fr))` }}
                  >
                    <div className="px-4 py-3">
                      <p className="font-syne text-sm font-bold text-white">
                        <span className="font-outfit tabular-nums text-glow">{plan.slot_times?.[s.slot - 1]}</span>
                        <span className="ml-1.5 font-mono text-[10px] font-normal text-slate-500">C{s.slot}</span>
                      </p>
                      <p className={`text-[11px] ${s.overbooked ? "text-red-300" : s.free === 0 ? "text-gold" : "text-slate-500"}`}>
                        {s.overbooked ? "Surbooké" : s.free === 0 ? "Complet" : `${s.free} libre${s.free > 1 ? "s" : ""}`}
                      </p>
                    </div>
                    {[...Array(plan.boards)].map((_, bi) => {
                      const b = cells[bi];
                      return (
                        <div key={bi} className="p-1.5">
                          {b ? (
                            <div
                              data-testid={`planning-cell-${s.slot}-${bi + 1}`}
                              title={`${b.name} — ${EXP_LABELS[b.experience]}`}
                              className={`h-full rounded-lg border px-2.5 py-2 text-[11px] leading-tight ${
                                b.experience === "corporate" ? "border-gold/40 bg-gold/15 text-gold" : "border-glow/40 bg-glow/10 text-white"
                              } ${b.status === "pending" ? "opacity-60 border-dashed" : ""}`}
                            >
                              <p className="truncate font-medium">{b.name}</p>
                              <p className="truncate text-[10px] opacity-70">{EXP_LABELS[b.experience]}{b.status === "pending" ? " · à confirmer" : ""}</p>
                            </div>
                          ) : (
                            <div data-testid={`planning-cell-${s.slot}-${bi + 1}`} className="h-full min-h-[46px] rounded-lg border border-dashed border-white/10 grid place-items-center text-[10px] text-slate-600">Libre</div>
                          )}
                        </div>
                      );
                    })}
                  </motion.div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-panel/70 p-5 backdrop-blur-xl" data-testid="planning-unassigned">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">À placer sur un créneau ({plan.unassigned.length})</p>
            {plan.unassigned.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">Toutes les réservations du jour ont un créneau.</p>
            ) : (
              <ul className="mt-4 divide-y divide-white/5">
                {plan.unassigned.map((b) => (
                  <li key={b.id} className="flex flex-wrap items-center justify-between gap-3 py-3" data-testid={`unassigned-${b.id}`}>
                    <div>
                      <p className="text-sm font-medium text-white">{b.name} <span className="text-slate-500">· {EXP_LABELS[b.experience]} · {b.participants} pers.</span></p>
                      <p className="text-[11px] text-slate-500">{b.email}{b.status === "pending" ? " · en attente de confirmation" : ""}</p>
                    </div>
                    <select
                      data-testid={`assign-slot-${b.id}`}
                      defaultValue=""
                      disabled={busyId === b.id}
                      onChange={(e) => e.target.value && assign(b.id, Number(e.target.value))}
                      className="rounded-full border border-glow/40 bg-deep px-3 py-1.5 text-xs text-glow outline-none"
                    >
                      <option value="">Choisir un créneau…</option>
                      {plan.slots.map((s) => (
                        <option key={s.slot} value={s.slot} disabled={s.free < boardsNeeded(b, plan.boards)}>
                          {plan.slot_times?.[s.slot - 1]} (C{s.slot}) — {s.free} libre{s.free > 1 ? "s" : ""}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default AdminPlanning;
