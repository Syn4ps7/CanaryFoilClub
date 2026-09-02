import { motion } from "framer-motion";
import { Handshake } from "lucide-react";
import { eur } from "@/lib/adminApi";

export const EXP_LABELS = {
  discovery: "Discovery",
  duo: "Duo VIP",
  drone: "Option Drone",
  corporate: "Corporate Sunset",
  testdrive: "Test Drive",
};

export const STATUS_META = {
  pending: { label: "En attente", cls: "border-amber-400/40 bg-amber-400/10 text-amber-300" },
  confirmed: { label: "Confirmée", cls: "border-glow/40 bg-glow/10 text-glow" },
  completed: { label: "Réalisée", cls: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" },
  cancelled: { label: "Annulée", cls: "border-red-400/40 bg-red-400/10 text-red-300" },
};

const fmtDate = (d) => {
  if (!d) return "—";
  const dt = new Date(d);
  return isNaN(dt) ? d : dt.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
};

const BookingsTable = ({ bookings = [], onUpdate, busyId }) => (
  <motion.section
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
    data-testid="recent-bookings"
    className="rounded-2xl border border-white/10 bg-panel/70 backdrop-blur-xl"
  >
    <div className="flex items-center justify-between px-5 sm:px-6 pt-5 sm:pt-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">10 dernières réservations</p>
      <p className="font-mono text-[10px] text-slate-500">{bookings.length} affichées</p>
    </div>
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[820px] text-left text-sm">
        <thead>
          <tr className="border-y border-white/10 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
            <th className="px-5 sm:px-6 py-3 font-normal">Client</th>
            <th className="px-3 py-3 font-normal">Offre</th>
            <th className="px-3 py-3 font-normal">Session</th>
            <th className="px-3 py-3 font-normal text-center">Pers.</th>
            <th className="px-3 py-3 font-normal text-right">Montant</th>
            <th className="px-3 py-3 font-normal text-center">Partenaire</th>
            <th className="px-5 sm:px-6 py-3 font-normal">Statut</th>
          </tr>
        </thead>
        <tbody>
          {bookings.length === 0 && (
            <tr>
              <td colSpan={7} className="px-6 py-10 text-center text-slate-500" data-testid="bookings-empty">
                Aucune réservation pour le moment.
              </td>
            </tr>
          )}
          {bookings.map((b) => (
            <tr key={b.id} data-testid={`booking-row-${b.id}`} className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
              <td className="px-5 sm:px-6 py-3.5">
                <p className="font-medium text-white">{b.name}</p>
                <p className="text-[11px] text-slate-500">{b.email}{b.hotel ? ` · ${b.hotel}` : ""}</p>
              </td>
              <td className="px-3 py-3.5 text-slate-300">{EXP_LABELS[b.experience] || b.experience}</td>
              <td className="px-3 py-3.5 text-slate-300 whitespace-nowrap">{fmtDate(b.date)}</td>
              <td className="px-3 py-3.5 text-center text-slate-300">{b.participants}</td>
              <td className="px-3 py-3.5 text-right font-syne font-bold text-white">{eur(b.amount)}</td>
              <td className="px-3 py-3.5 text-center">
                <button
                  data-testid={`booking-partner-toggle-${b.id}`}
                  onClick={() => onUpdate(b.id, { partner: !b.partner })}
                  disabled={busyId === b.id}
                  title={b.partner ? `Apport partenaire${b.partner_name ? ` — ${b.partner_name}` : ""} (20 %)` : "Marquer comme apport partenaire"}
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                    b.partner ? "border-gold/50 bg-gold/10 text-gold" : "border-white/10 text-slate-500 hover:border-white/30"
                  }`}
                >
                  <Handshake size={12} />
                  {b.partner ? "20 %" : "—"}
                </button>
              </td>
              <td className="px-5 sm:px-6 py-3.5">
                <select
                  data-testid={`booking-status-select-${b.id}`}
                  value={b.status}
                  disabled={busyId === b.id}
                  onChange={(e) => onUpdate(b.id, { status: e.target.value })}
                  className={`rounded-full border px-3 py-1 text-[11px] font-medium outline-none cursor-pointer ${STATUS_META[b.status]?.cls || ""}`}
                  style={{ backgroundColor: "#0A1322" }}
                >
                  {Object.entries(STATUS_META).map(([k, v]) => (
                    <option key={k} value={k} style={{ backgroundColor: "#0F1C30", color: "#fff" }}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </motion.section>
);

export default BookingsTable;
