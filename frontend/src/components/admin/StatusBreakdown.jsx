import { motion } from "framer-motion";
import { eur } from "@/lib/adminApi";

const ROWS = [
  { key: "pending", label: "En attente", cls: "text-amber-300", note: "Hors CA — à confirmer" },
  { key: "confirmed", label: "Confirmées", cls: "text-glow", note: "Comptées dans le CA" },
  { key: "completed", label: "Réalisées", cls: "text-emerald-300", note: "Comptées dans le CA" },
  { key: "cancelled", label: "Annulées", cls: "text-red-300", note: "Hors CA" },
];

const StatusBreakdown = ({ stats }) => {
  const counts = stats.status_counts || {};
  const rev = stats.revenue_by_status || {};
  const gift = stats.by_offer?.gift || 0;
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
      data-testid="status-breakdown"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Réservations → chiffre d'affaires</p>
        <p className="text-[11px] text-slate-500">CA = réservations confirmées + réalisées (comptées le jour de la confirmation) + bons cadeaux activés</p>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {ROWS.map((r) => (
          <div key={r.key} data-testid={`status-${r.key}`} className="rounded-xl border border-white/10 bg-deep/60 px-4 py-3">
            <p className={`font-mono text-[10px] uppercase tracking-[0.18em] ${r.cls}`}>{r.label}</p>
            <p className="mt-1 font-outfit text-2xl font-semibold tabular-nums text-white">{counts[r.key] || 0}</p>
            <p className="text-[11px] text-slate-500">
              {r.key in rev ? <span className={`font-outfit tabular-nums ${r.cls}`}>{eur(rev[r.key])}</span> : r.note}
              {r.key in rev && <span className="text-slate-500"> · {r.note}</span>}
            </p>
          </div>
        ))}
        <div data-testid="status-gift" className="rounded-xl border border-gold/25 bg-gold/5 px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">Bons cadeaux</p>
          <p className="mt-1 font-outfit text-2xl font-semibold tabular-nums text-white">{eur(gift)}</p>
          <p className="text-[11px] text-slate-500">Encaissés à l'activation</p>
        </div>
      </div>
      <p className="mt-3 text-[11px] text-slate-500" data-testid="status-check">
        Vérification : {(counts.confirmed || 0) + (counts.completed || 0)} sessions confirmées + réalisées = {stats.sessions.total} sessions comptées ·{" "}
        {eur((rev.confirmed || 0) + (rev.completed || 0) + gift)} = CA total {eur(stats.revenue.total)}
      </p>
    </motion.section>
  );
};

export default StatusBreakdown;
