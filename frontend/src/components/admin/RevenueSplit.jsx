import { motion } from "framer-motion";
import { eur } from "@/lib/adminApi";

const OFFERS = [
  { key: "b2c", label: "B2C classique", sub: "Discovery · Duo VIP · Test Drive", color: "#00F0FF" },
  { key: "corporate", label: "Pack B2B Corporate Sunset", sub: "890 € — privatisation golden hour", color: "#D4AF37" },
  { key: "drone", label: "Options Drone 4K", sub: "+50 € / participant", color: "#00C2CB" },
  { key: "gift", label: "Bons cadeaux", sub: "Encaissés à l'activation", color: "#F5D06F" },
];

const RevenueSplit = ({ byOffer = {} }) => {
  const total = Object.values(byOffer).reduce((a, b) => a + b, 0) || 1;
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
      data-testid="revenue-split"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl"
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Répartition du CA par offre</p>
      <div className="mt-6 space-y-5">
        {OFFERS.map((o, i) => {
          const val = byOffer[o.key] || 0;
          const pct = Math.round((val / total) * 100);
          return (
            <div key={o.key} data-testid={`revenue-offer-${o.key}`}>
              <div className="flex items-baseline justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-white">{o.label}</p>
                  <p className="text-[11px] text-slate-500">{o.sub}</p>
                </div>
                <div className="text-right">
                  <p className="font-outfit text-lg font-semibold tabular-nums" style={{ color: o.color }}>{eur(val)}</p>
                  <p className="font-mono text-[10px] text-slate-500">{pct}%</p>
                </div>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.9, delay: 0.4 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
                  className="h-full rounded-full"
                  style={{ background: o.color, boxShadow: `0 0 12px ${o.color}66` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </motion.section>
  );
};

export default RevenueSplit;
