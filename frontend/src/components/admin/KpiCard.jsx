import { motion } from "framer-motion";

const KpiCard = ({ label, value, sub, icon: Icon, accent = "glow", delay = 0, testId }) => (
  <motion.div
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
    data-testid={testId}
    className="relative overflow-hidden rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl transition-colors duration-300 hover:border-glow/40"
  >
    <div
      className="pointer-events-none absolute inset-0"
      style={{ background: "radial-gradient(circle at 50% 0%, rgba(0,240,255,0.10) 0%, transparent 70%)" }}
    />
    <div className="relative flex items-start justify-between gap-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">{label}</p>
      {Icon && (
        <span className={`grid h-9 w-9 place-items-center rounded-full border border-white/10 ${accent === "gold" ? "text-gold" : "text-glow"}`}>
          <Icon size={16} />
        </span>
      )}
    </div>
    <p className={`relative mt-4 font-syne text-3xl sm:text-4xl font-extrabold tracking-tight ${accent === "gold" ? "text-gold" : "text-white"}`}>
      {value}
    </p>
    {sub && <p className="relative mt-2 text-xs text-slate-400">{sub}</p>}
  </motion.div>
);

export default KpiCard;
