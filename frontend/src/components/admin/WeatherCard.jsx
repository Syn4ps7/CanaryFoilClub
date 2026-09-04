import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Wind, Waves, Navigation, Thermometer, MapPin } from "lucide-react";
import { adminApi } from "@/lib/adminApi";

const LEVEL = {
  ideal: { label: "Idéal", cls: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" },
  good: { label: "Bon", cls: "border-glow/40 bg-glow/10 text-glow" },
  caution: { label: "Limite", cls: "border-amber-400/40 bg-amber-400/10 text-amber-300" },
  nogo: { label: "Déconseillé", cls: "border-red-400/40 bg-red-400/10 text-red-300" },
  unknown: { label: "—", cls: "border-white/15 text-slate-400" },
};

const Metric = ({ icon: Icon, label, value, unit, sub, testId }) => (
  <div className="rounded-xl border border-white/10 bg-deep/60 px-4 py-3" data-testid={testId}>
    <div className="flex items-center gap-2 text-slate-400">
      <Icon size={13} className="text-glow" />
      <span className="font-mono text-[10px] uppercase tracking-[0.18em]">{label}</span>
    </div>
    <p className="mt-2 font-outfit text-2xl font-semibold tabular-nums text-white">
      {value ?? "—"}
      {value != null && <span className="ml-1 text-xs font-medium text-slate-400">{unit}</span>}
    </p>
    {sub && <p className="text-[11px] text-slate-500">{sub}</p>}
  </div>
);

const WeatherCard = ({ day }) => {
  const [w, setW] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setW(null);
    setError("");
    adminApi
      .get("/admin/weather", { params: { day } })
      .then(({ data }) => setW(data))
      .catch((e) => {
        const detail = e?.response?.data?.detail;
        setError(typeof detail === "string" && detail.length < 120 ? detail : "Prévisions indisponibles pour cette date");
      });
  }, [day]);

  const lvl = LEVEL[w?.spot?.level] || LEVEL.unknown;
  const s = w?.summary;
  const maxWind = Math.max(30, ...(w?.hourly?.map((h) => h.gust || 0) || [30]));

  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      data-testid="weather-card"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Météo du spot — Costa Adeje</p>
          <div className="mt-2 flex items-center gap-2">
            <MapPin size={15} className="text-gold" />
            <p className="font-syne text-lg font-bold text-white" data-testid="weather-spot">{w ? w.spot.spot : error || "Chargement…"}</p>
            {w && <span data-testid="weather-level" className={`rounded-full border px-2.5 py-0.5 text-[11px] ${lvl.cls}`}>{lvl.label}</span>}
          </div>
          {w && <p className="mt-1 max-w-xl text-xs text-slate-400" data-testid="weather-reason">{w.spot.reason}</p>}
        </div>
        <p className="text-[10px] text-slate-600">{w?.source || "Weather data by Open-Meteo.com"}</p>
      </div>

      {s && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric icon={Wind} label="Vent moyen" value={s.wind_avg} unit="km/h" sub={`Rafales ${s.gust_max ?? "—"} km/h · max ${s.wind_max ?? "—"}`} testId="weather-wind" />
            <Metric icon={Navigation} label="Direction vent" value={s.wind_dir_label} unit={s.wind_dir != null ? `${s.wind_dir}°` : ""} sub="Alizés N-NE = côte SO abritée" testId="weather-wind-dir" />
            <Metric icon={Waves} label="Houle" value={s.wave_avg} unit="m" sub={`Max ${s.wave_max ?? "—"} m · période ${s.period_avg ?? "—"} s · ${s.wave_dir_label ?? "—"}`} testId="weather-wave" />
            <Metric icon={Thermometer} label="Température" value={s.temp_max} unit="°C" sub="Maximum de la journée" testId="weather-temp" />
          </div>

          <div className="mt-5" data-testid="weather-hourly">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">Vent & houle heure par heure (8h → 20h)</p>
            <div className="flex items-end gap-1.5 overflow-x-auto pb-1">
              {w.hourly.map((h) => {
                const pctW = Math.round(((h.wind || 0) / maxWind) * 100);
                const pctG = Math.round(((h.gust || 0) / maxWind) * 100);
                return (
                  <div key={h.time} className="flex min-w-[44px] flex-1 flex-col items-center gap-1" title={`${h.time} — vent ${h.wind} km/h, rafales ${h.gust} km/h, houle ${h.wave} m`}>
                    <span className="font-outfit text-[11px] tabular-nums text-slate-300">{h.wave ?? "—"}<span className="text-[9px] text-slate-500">m</span></span>
                    <div className="relative h-16 w-full rounded-md bg-white/5">
                      <div className="absolute bottom-0 left-0 right-0 rounded-md bg-glow/25" style={{ height: `${pctG}%` }} />
                      <div className="absolute bottom-0 left-0 right-0 rounded-md bg-glow" style={{ height: `${pctW}%`, boxShadow: "0 0 10px rgba(0,240,255,0.4)" }} />
                    </div>
                    <span className="font-mono text-[9px] text-slate-500">{h.time.slice(0, 2)}h</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </motion.section>
  );
};

export default WeatherCard;
