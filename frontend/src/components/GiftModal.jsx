import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Gift } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useLanguage } from "@/i18n/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PRICES = { discovery: 145, duo: 280 };
const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-gold/70";
const EMPTY = { buyer_name: "", buyer_email: "", recipient_name: "", message: "", experience: "discovery", participants: 1 };

const Label = ({ children }) => <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{children}</label>;

const GiftModal = ({ open, onClose }) => {
  const { t, lang } = useLanguage();
  const [form, setForm] = useState(EMPTY);
  const [sending, setSending] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const value = form.experience === "duo" ? PRICES.duo : PRICES.discovery * Number(form.participants || 1);

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await axios.post(`${API}/vouchers`, { ...form, participants: Number(form.participants), lang });
      toast.success(t.gift.success);
      onClose();
      setForm(EMPTY);
    } catch {
      toast.error(t.toast.error);
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }} onClick={onClose} className="fixed inset-0 z-[90] bg-abyss/80 backdrop-blur-sm" />
          <motion.aside
            data-testid="gift-modal"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            className="fixed right-0 top-0 z-[95] h-full w-full max-w-md overflow-y-auto border-l border-gold/20 bg-panel"
          >
            <div className="p-7 sm:p-9">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-gold">{t.gift.caption}</p>
                  <h3 className="mt-2 font-syne text-2xl font-bold">{t.gift.modalTitle}</h3>
                  <p className="mt-2 text-sm text-slate-400">{t.gift.modalSub}</p>
                </div>
                <button data-testid="gift-modal-close" onClick={onClose} aria-label="Close" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-gold/60 hover:text-gold">
                  <X size={18} />
                </button>
              </div>
              <form onSubmit={submit} className="mt-8 space-y-5">
                <div>
                  <Label>{t.gift.buyerName}</Label>
                  <input data-testid="gift-input-buyer-name" required minLength={2} value={form.buyer_name} onChange={set("buyer_name")} className={inputCls} placeholder="Sophie Martin" />
                </div>
                <div>
                  <Label>{t.gift.buyerEmail}</Label>
                  <input data-testid="gift-input-buyer-email" type="email" required value={form.buyer_email} onChange={set("buyer_email")} className={inputCls} placeholder="you@email.com" />
                </div>
                <div>
                  <Label>{t.gift.recipient}</Label>
                  <input data-testid="gift-input-recipient" required minLength={2} value={form.recipient_name} onChange={set("recipient_name")} className={inputCls} placeholder="Thomas" />
                </div>
                <div className="grid grid-cols-[1fr_96px] gap-4">
                  <div>
                    <Label>{t.gift.experience}</Label>
                    <select data-testid="gift-select-experience" value={form.experience} onChange={set("experience")} className={inputCls} style={{ backgroundColor: "#0A1322" }}>
                      {Object.entries(t.gift.options).map(([k, v]) => (
                        <option key={k} value={k} style={{ backgroundColor: "#0F1C30", color: "#fff" }}>{v}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label>{t.gift.participants}</Label>
                    <input data-testid="gift-input-participants" type="number" min={1} max={3} disabled={form.experience === "duo"} value={form.experience === "duo" ? 2 : form.participants} onChange={set("participants")} className={`${inputCls} disabled:opacity-50`} />
                  </div>
                </div>
                <div>
                  <Label>{t.gift.message}</Label>
                  <textarea data-testid="gift-input-message" rows={3} maxLength={300} value={form.message} onChange={set("message")} className={`${inputCls} resize-none`} />
                </div>
                <div className="flex items-center justify-between rounded-xl border border-gold/30 bg-gold/5 px-4 py-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold">{t.gift.value}</span>
                  <span data-testid="gift-value" className="font-outfit text-2xl font-semibold tabular-nums text-white">{value} €</span>
                </div>
                <motion.button
                  data-testid="gift-form-submit"
                  type="submit"
                  disabled={sending}
                  whileHover={{ scale: sending ? 1 : 1.02 }}
                  whileTap={{ scale: sending ? 1 : 0.97 }}
                  className="flex w-full items-center justify-center gap-2 rounded-full bg-gold py-4 font-syne text-sm font-bold text-abyss disabled:opacity-60"
                >
                  <Gift size={16} /> {sending ? t.gift.submitting : t.gift.submit}
                </motion.button>
              </form>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default GiftModal;
