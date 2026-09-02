import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useLanguage } from "@/i18n/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const BookingModal = ({ open, preset, onClose }) => {
  const { t, lang } = useLanguage();
  const [sending, setSending] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    experience: "discovery",
    date: "",
    participants: 1,
    hotel: "",
    notes: "",
  });

  useEffect(() => {
    if (open && preset) setForm((f) => ({ ...f, experience: preset }));
  }, [open, preset]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await axios.post(`${API}/booking`, { ...form, participants: Number(form.participants), lang });
      toast.success(t.toast.success);
      onClose();
      setForm({ name: "", email: "", phone: "", experience: "discovery", date: "", participants: 1, hotel: "", notes: "" });
    } catch (err) {
      toast.error(t.toast.error);
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            onClick={onClose}
            className="fixed inset-0 z-[90] bg-abyss/80 backdrop-blur-sm"
          />
          <motion.aside
            data-testid="booking-modal"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            className="fixed right-0 top-0 z-[95] h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-panel"
          >
            <div className="p-7 sm:p-9">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-syne text-2xl font-bold">{t.booking.title}</h3>
                  <p className="mt-2 text-sm text-slate-400">{t.booking.sub}</p>
                </div>
                <button
                  data-testid="modal-booking-close-button"
                  onClick={onClose}
                  className="grid place-items-center h-10 w-10 rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow"
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={submit} className="mt-8 space-y-5">
                <div>
                  <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.name}</label>
                  <input data-testid="booking-input-name" required minLength={2} value={form.name} onChange={set("name")} className={inputCls} placeholder="Alexandra Dupont" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.email}</label>
                    <input data-testid="booking-input-email" type="email" required value={form.email} onChange={set("email")} className={inputCls} placeholder="you@hotel.com" />
                  </div>
                  <div>
                    <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.phone}</label>
                    <input data-testid="booking-input-phone" required minLength={6} value={form.phone} onChange={set("phone")} className={inputCls} placeholder="+34 600 000 000" />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.experience}</label>
                  <select
                    data-testid="booking-select-experience"
                    value={form.experience}
                    onChange={set("experience")}
                    className={inputCls}
                    style={{ backgroundColor: "#0A1322" }}
                  >
                    {Object.entries(t.booking.options).map(([k, v]) => (
                      <option key={k} value={k} style={{ backgroundColor: "#0F1C30", color: "#fff" }}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-5">
                  <div>
                    <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.date}</label>
                    <input data-testid="booking-input-date" type="date" required value={form.date} onChange={set("date")} className={inputCls} />
                  </div>
                  <div>
                    <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.participants}</label>
                    <input data-testid="booking-input-participants" type="number" min={1} max={12} required value={form.participants} onChange={set("participants")} className={inputCls} />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.hotel}</label>
                  <input data-testid="booking-input-hotel" value={form.hotel} onChange={set("hotel")} className={inputCls} placeholder="Bahía del Duque, Abama…" />
                </div>
                <div>
                  <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{t.booking.notes}</label>
                  <textarea data-testid="booking-input-notes" rows={3} value={form.notes} onChange={set("notes")} className={`${inputCls} resize-none`} />
                </div>
                <motion.button
                  data-testid="booking-form-submit"
                  type="submit"
                  disabled={sending}
                  whileHover={{ scale: sending ? 1 : 1.02 }}
                  whileTap={{ scale: sending ? 1 : 0.97 }}
                  className="w-full rounded-full bg-glow py-4 font-syne text-sm font-bold text-abyss btn-glow disabled:opacity-60"
                >
                  {sending ? t.booking.submitting : t.booking.submit}
                </motion.button>
              </form>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default BookingModal;
