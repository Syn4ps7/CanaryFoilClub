import { motion } from "framer-motion";
import { Handshake, Bell, BellRing, Star, MessageSquareQuote, ShieldCheck, ShieldAlert } from "lucide-react";
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

const BookingsTable = ({ bookings = [], onUpdate, onReminder = () => {}, onReviewRequest = () => {}, busyId, title = "Réservations", slotTimes, allSlotTimes }) => {
  const slotLabel = (s) => (allSlotTimes && allSlotTimes[s - 1]) || `C${s}`;
  return (
  <motion.section
    initial={{ opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
    data-testid="recent-bookings"
    className="rounded-2xl border border-white/10 bg-panel/70 backdrop-blur-xl"
  >
    <div className="flex items-center justify-between px-5 sm:px-6 pt-5 sm:pt-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">{title}</p>
      <p className="font-mono text-[10px] text-slate-500" data-testid="bookings-count">{bookings.length} affichée{bookings.length > 1 ? "s" : ""}</p>
    </div>
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[1000px] text-left text-sm">
        <thead>
          <tr className="border-y border-white/10 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
            <th className="px-5 sm:px-6 py-3 font-normal">Client</th>
            <th className="px-3 py-3 font-normal">Offre</th>
            <th className="px-3 py-3 font-normal">Session</th>
            <th className="px-3 py-3 font-normal text-center">Pers.</th>
            <th className="px-3 py-3 font-normal text-right">Montant</th>
            <th className="px-3 py-3 font-normal text-center">Rappel J-1</th>
            <th className="px-3 py-3 font-normal text-center">Avis</th>
            <th className="px-3 py-3 font-normal text-center">Partenaire</th>
            <th className="px-5 sm:px-6 py-3 font-normal">Statut</th>
          </tr>
        </thead>
        <tbody>
          {bookings.length === 0 && (
            <tr>
              <td colSpan={9} className="px-6 py-10 text-center text-slate-500" data-testid="bookings-empty">
                Aucune réservation pour le moment.
              </td>
            </tr>
          )}
          {bookings.map((b) => (
            <tr key={b.id} data-testid={`booking-row-${b.id}`} className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
              <td className="px-5 sm:px-6 py-3.5">
                <p className="font-medium text-white">{b.name}</p>
                <p className="text-[11px] text-slate-500">{b.email}{b.hotel ? ` · ${b.hotel}` : ""}</p>
                {b.paid_at && (
                  <span data-testid={`booking-paid-${b.id}`} className="mt-1 mr-1 inline-flex items-center rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2 py-0.5 text-[10px] text-emerald-300">Payé en ligne</span>
                )}
                {b.minor && (
                  <button
                    data-testid={`booking-minor-toggle-${b.id}`}
                    onClick={() => onUpdate(b.id, { parental_auth_received: !b.parental_auth_received })}
                    disabled={busyId === b.id}
                    title={b.parental_auth_received ? "Autorisation parentale reçue — cliquer pour annuler" : "Mineur : autorisation parentale à récupérer — cliquer quand reçue"}
                    className={`mt-1 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${
                      b.parental_auth_received ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-amber-400/50 bg-amber-400/10 text-amber-300"
                    }`}
                  >
                    {b.parental_auth_received ? <ShieldCheck size={11} /> : <ShieldAlert size={11} />}
                    {b.parental_auth_received ? "Mineur · autorisation reçue" : "Mineur · autorisation à recevoir"}
                  </button>
                )}
              </td>
              <td className="px-3 py-3.5 text-slate-300">{EXP_LABELS[b.experience] || b.experience}</td>
              <td className="px-3 py-3.5 text-slate-300 whitespace-nowrap">
                {fmtDate(b.date)}
                {slotTimes ? (
                  <select
                    data-testid={`booking-slot-select-${b.id}`}
                    value={b.slot || 0}
                    disabled={busyId === b.id}
                    onChange={(e) => onUpdate(b.id, { slot: Number(e.target.value) })}
                    className="ml-2 rounded-full border border-white/15 px-2 py-0.5 text-[10px] text-slate-300 outline-none"
                    style={{ backgroundColor: "#0A1322" }}
                  >
                    <option value={0}>Heure —</option>
                    {slotTimes.map((t, i) => (
                      <option key={i + 1} value={i + 1}>{t} · C{i + 1}</option>
                    ))}
                  </select>
                ) : (
                  b.slot && <span className="ml-2 rounded-full border border-white/15 px-2 py-0.5 font-outfit text-[10px] tabular-nums text-slate-300">{slotLabel(b.slot)}</span>
                )}
              </td>
              <td className="px-3 py-3.5 text-center text-slate-300">{b.participants}</td>
              <td className="px-3 py-3.5 text-right font-outfit font-semibold tabular-nums text-white">{eur(b.amount)}</td>
              <td className="px-3 py-3.5 text-center">
                {["confirmed", "completed"].includes(b.status) ? (
                  <button
                    data-testid={`booking-reminder-${b.id}`}
                    onClick={() => onReminder(b.id)}
                    disabled={busyId === b.id}
                    title={b.reminder_sent ? `Rappel envoyé le ${new Date(b.reminder_sent_at).toLocaleString("fr-FR")}${b.reminder_spot ? ` — RDV ${b.reminder_spot}` : ""}. Cliquer pour renvoyer.` : "Envoyer le rappel veille maintenant"}
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                      b.reminder_sent ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-slate-400 hover:border-glow/50 hover:text-glow"
                    }`}
                  >
                    {b.reminder_sent ? <BellRing size={12} /> : <Bell size={12} />}
                    {b.reminder_sent ? "Envoyé" : "Envoyer"}
                  </button>
                ) : (
                  <span className="text-[11px] text-slate-600">—</span>
                )}
              </td>
              <td className="px-3 py-3.5 text-center">
                {b.review_id ? (
                  <span data-testid={`booking-review-received-${b.id}`} title="Avis reçu — voir l'onglet Avis" className="inline-flex items-center gap-1 rounded-full border border-gold/40 bg-gold/10 px-2.5 py-1 text-[11px] text-gold">
                    <Star size={12} className="fill-gold" /> Reçu
                  </span>
                ) : ["confirmed", "completed"].includes(b.status) ? (
                  <button
                    data-testid={`booking-review-request-${b.id}`}
                    onClick={() => onReviewRequest(b.id)}
                    disabled={busyId === b.id}
                    title={b.review_request_sent ? `Demande d'avis envoyée le ${new Date(b.review_request_sent_at).toLocaleString("fr-FR")}. Cliquer pour renvoyer.` : "Envoyer la demande d'avis maintenant"}
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                      b.review_request_sent ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-slate-400 hover:border-gold/50 hover:text-gold"
                    }`}
                  >
                    <MessageSquareQuote size={12} />
                    {b.review_request_sent ? "Demandé" : "Demander"}
                  </button>
                ) : (
                  <span className="text-[11px] text-slate-600">—</span>
                )}
              </td>
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
};

export default BookingsTable;
