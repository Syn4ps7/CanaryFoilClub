import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { adminApi, eur, formatApiError } from "@/lib/adminApi";

const shiftDays = (s, n) => {
  const d = new Date(`${s}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

const fmtShort = (s) => new Date(`${s}T12:00:00Z`).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });

const tone = (o) => (o === 0 ? "text-slate-500" : o < 40 ? "text-amber-300" : o < 80 ? "text-glow" : "text-emerald-300");

const WeekView = ({ anchor, today, onPickDay, onLogout }) => {
  const [week, setWeek] = useState(null);
  const [start, setStart] = useState(anchor);

  useEffect(() => {
    adminApi
      .get("/admin/planning/week", { params: { start } })
      .then(({ data }) => setWeek(data))
      .catch((err) => (err?.response?.status === 401 ? onLogout() : toast.error(formatApiError(err))));
  }, [start, onLogout]);

  const totals = week?.days.reduce((a, d) => ({ used: a.used + d.used, cap: a.cap + d.capacity, rev: a.rev + d.revenue }), { used: 0, cap: 0, rev: 0 });
  const emptyDays = week?.days.filter((d) => d.used === 0).length ?? 0;

  return (
    <div className="space-y-4" data-testid="week-view">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-panel/70 px-5 py-4 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <button data-testid="week-prev" onClick={() => setStart((s) => shiftDays(s, -7))} className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"><ChevronLeft size={16} /></button>
          <p className="font-syne text-sm font-bold text-white capitalize" data-testid="week-range">
            {week ? `${fmtShort(week.start)} → ${fmtShort(week.end)}` : "…"}
          </p>
          <button data-testid="week-next" onClick={() => setStart((s) => shiftDays(s, 7))} className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"><ChevronRight size={16} /></button>
          <button data-testid="week-current" onClick={() => setStart(today)} className="rounded-full border border-white/15 px-4 py-2 text-xs text-slate-300 transition-colors hover:border-glow/60 hover:text-glow">Cette semaine</button>
        </div>
        {totals && (
          <div className="flex items-center gap-5 text-xs text-slate-400" data-testid="week-totals">
            <span>Occupation <span className="font-outfit text-base font-semibold tabular-nums text-white">{Math.round((totals.used / totals.cap) * 100)} %</span></span>
            <span>CA <span className="font-outfit text-base font-semibold tabular-nums text-white">{eur(totals.rev)}</span></span>
            <span className={emptyDays ? "text-amber-300" : "text-emerald-300"}>{emptyDays} jour{emptyDays > 1 ? "s" : ""} creux</span>
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
        {week?.days.map((d, i) => {
          const isToday = d.date === today;
          const pendingPct = Math.round((d.pending / d.capacity) * 100);
          return (
            <motion.button
              key={d.date}
              data-testid={`week-day-${d.date}`}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              onClick={() => onPickDay(d.date)}
              className={`group relative flex flex-col rounded-2xl border p-4 text-left transition-colors ${
                isToday ? "border-glow/50 bg-glow/5" : d.used === 0 ? "border-dashed border-white/15 bg-panel/40 hover:border-amber-400/40" : "border-white/10 bg-panel/70 hover:border-glow/40"
              }`}
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500 capitalize">{fmtShort(d.date)}</p>
              <p className={`mt-3 font-outfit text-3xl font-semibold tabular-nums ${tone(d.occupancy)}`}>{d.occupancy} %</p>
              <p className="text-[11px] text-slate-500">{d.used} / {d.capacity} slots</p>
              <div className="mt-3 flex h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                <div className="h-full bg-glow" style={{ width: `${d.occupancy}%` }} />
                <div className="h-full bg-amber-400/60" style={{ width: `${pendingPct}%` }} />
              </div>
              <div className="mt-3 space-y-0.5 text-[11px]">
                <p className="text-slate-300">{d.sessions} session{d.sessions > 1 ? "s" : ""} · <span className="font-outfit tabular-nums">{eur(d.revenue)}</span></p>
                {d.pending_count > 0 && <p className="text-amber-300">{d.pending_count} en attente</p>}
                {d.unassigned > 0 && <p className="text-slate-500">{d.unassigned} à placer</p>}
                {d.used === 0 && d.pending_count === 0 && <p className="text-amber-300/80">Jour creux — à remplir</p>}
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

export default WeekView;
