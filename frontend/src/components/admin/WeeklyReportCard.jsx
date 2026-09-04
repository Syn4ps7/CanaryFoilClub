import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Mail, FileBarChart } from "lucide-react";
import { adminApi, eur, formatApiError } from "@/lib/adminApi";

const WeeklyReportCard = () => {
  const [r, setR] = useState(null);
  const [sending, setSending] = useState(false);

  const load = () => adminApi.get("/admin/reports/weekly").then(({ data }) => setR(data)).catch(() => setR(null));
  useEffect(() => {
    load();
  }, []);

  const send = async () => {
    setSending(true);
    try {
      await adminApi.post("/admin/reports/weekly/send");
      toast.success("Bilan hebdo envoyé à l'adresse propriétaire");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.32, ease: [0.16, 1, 0.3, 1] }}
      data-testid="weekly-report-card"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Bilan hebdo — lundi matin</p>
        <FileBarChart size={15} className="text-glow" />
      </div>
      {r ? (
        <>
          <p className="mt-3 text-xs text-slate-500">Semaine du <span className="text-white">{r.week_label}</span></p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {[
              ["CA", eur(r.revenue), "text-glow"],
              ["Sessions", r.sessions, "text-white"],
              ["Occupation", `${r.occupancy} %`, "text-white"],
              ["Jours creux", r.empty_days, r.empty_days > 2 ? "text-amber-300" : "text-white"],
            ].map(([l, v, c]) => (
              <div key={l} className="rounded-xl border border-white/10 bg-deep/60 px-3 py-2">
                <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-500">{l}</p>
                <p className={`font-outfit text-lg font-semibold tabular-nums ${c}`}>{v}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-slate-500" data-testid="weekly-report-status">
            {r.last_sent?.sent ? `Envoyé le ${new Date(r.last_sent.sent_at).toLocaleString("fr-FR")}` : "Envoi automatique chaque lundi à 8h (heure des Canaries)"}
          </p>
        </>
      ) : (
        <div className="mt-4 h-24 animate-pulse rounded-xl bg-white/5" />
      )}
      <button
        data-testid="weekly-report-send"
        onClick={send}
        disabled={sending || !r}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full border border-glow/40 bg-glow/10 py-2.5 text-xs font-semibold text-glow transition-colors hover:bg-glow/20 disabled:opacity-40"
      >
        <Mail size={14} /> {sending ? "Envoi…" : "Envoyer le bilan maintenant"}
      </button>
    </motion.div>
  );
};

export default WeeklyReportCard;
