import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Area, Bar, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { TrendingUp } from "lucide-react";
import { adminApi, eur } from "@/lib/adminApi";

const fmtDay = (d) => new Date(`${d}T12:00:00Z`).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });

const TooltipBox = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border border-white/15 bg-abyss/95 px-3 py-2 text-xs shadow-xl" data-testid="revenue-chart-tooltip">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">{fmtDay(label)}</p>
      <p className="mt-1 font-outfit text-base font-semibold tabular-nums text-glow">{eur(d.revenue)}</p>
      <p className="text-slate-400">{d.bookings} réservation{d.bookings > 1 ? "s" : ""}{d.gift ? ` · bons ${eur(d.gift)}` : ""}</p>
      <p className="text-slate-500">Cumul : <span className="font-outfit tabular-nums text-white">{eur(d.cumulative)}</span></p>
    </div>
  );
};

const RevenueChart = () => {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    adminApi.get("/admin/stats/revenue-series", { params: { days } }).then(({ data }) => setData(data)).catch(() => setData(null));
  }, [days]);

  const avg = data ? data.total / days : 0;

  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
      data-testid="revenue-chart"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">CA encaissé — tendance</p>
          {data && (
            <p className="mt-2 flex items-baseline gap-3">
              <span className="font-outfit text-3xl font-semibold tabular-nums text-white" data-testid="revenue-chart-total">{eur(data.total)}</span>
              <span className="text-xs text-slate-400">sur {days} jours · {eur(avg)} / jour</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-full border border-white/15 bg-deep p-1">
            {[30, 90].map((n) => (
              <button key={n} data-testid={`revenue-chart-range-${n}`} onClick={() => setDays(n)} className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${days === n ? "bg-glow text-abyss" : "text-slate-300 hover:text-white"}`}>
                {n} j
              </button>
            ))}
          </div>
          <TrendingUp size={15} className="text-glow" />
        </div>
      </div>

      <div className="mt-5 h-56" data-testid="revenue-chart-canvas">
        {data && (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.series} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="cfcGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00F0FF" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#00F0FF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="date" tickFormatter={fmtDay} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={28} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v)} />
              <Tooltip content={<TooltipBox />} cursor={{ stroke: "rgba(0,240,255,0.3)" }} />
              <Bar dataKey="revenue" fill="rgba(0,240,255,0.35)" radius={[4, 4, 0, 0]} maxBarSize={18} />
              <Area type="monotone" dataKey="cumulative" stroke="#D4AF37" strokeWidth={2} fill="url(#cfcGlow)" dot={false} activeDot={{ r: 4, fill: "#D4AF37" }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
      {data?.best_day && data.best_day.revenue > 0 && (
        <p className="mt-2 text-[11px] text-slate-500" data-testid="revenue-chart-best">
          Meilleur jour : <span className="text-white">{fmtDay(data.best_day.date)}</span> · <span className="font-outfit tabular-nums text-glow">{eur(data.best_day.revenue)}</span> — barres = CA du jour, courbe dorée = cumul
        </p>
      )}
    </motion.section>
  );
};

export default RevenueChart;
