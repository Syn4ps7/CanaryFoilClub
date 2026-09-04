import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Gift, CheckCircle2, AlertCircle } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { useLanguage } from "@/i18n/LanguageContext";
import TermsCheckbox from "./TermsCheckbox";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const BookingModal = ({ open, preset, presetCode, onClose }) => {
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
    partner: false,
    partner_name: "",
    voucher_code: "",
    minor: false,
    minor_consent: false,
  });
  const [voucher, setVoucher] = useState(null);
  const [terms, setTerms] = useState(false);

  useEffect(() => {
    const code = form.voucher_code.trim();
    if (code.length < 8) {
      setVoucher(null);
      return;
    }
    const timer = setTimeout(() => {
      axios
        .get(`${API}/vouchers/check/${encodeURIComponent(code)}`)
        .then(({ data }) => setVoucher(data))
        .catch(() => setVoucher({ valid: false, reason: "not_found" }));
    }, 350);
    return () => clearTimeout(timer);
  }, [form.voucher_code]);

  useEffect(() => {
    if (open && preset) setForm((f) => ({ ...f, experience: preset }));
    if (open && presetCode) setForm((f) => ({ ...f, voucher_code: presetCode.toUpperCase() }));
  }, [open, preset, presetCode]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!terms) {
      toast.error(t.footer.termsRequired);
      return;
    }
    setSending(true);
    try {
      const { data: created } = await axios.post(`${API}/booking`, { ...form, participants: Number(form.participants), voucher_code: form.voucher_code.trim() || undefined, minor_consent: form.minor ? form.minor_consent : false, lang });
      if (created.amount > 0) {
        toast.success(t.payment.redirect);
        const { data: pay } = await axios.post(`${API}/payments/checkout`, { kind: "booking", ref_id: created.id, origin_url: window.location.origin });
        window.location.href = pay.checkout_url;
        return;
      }
      toast.success(t.toast.success);
      onClose();
      setForm({ name: "", email: "", phone: "", experience: "discovery", date: "", participants: 1, hotel: "", notes: "", partner: false, partner_name: "", voucher_code: "", minor: false, minor_consent: false });
      setVoucher(null);
      setTerms(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : t.toast.error);
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
            data-lenis-prevent
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
                <div className={`rounded-xl border p-4 ${form.minor ? "border-amber-400/40 bg-amber-400/5" : "border-white/10 bg-deep/60"}`}>
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      data-testid="booking-checkbox-minor"
                      type="checkbox"
                      checked={form.minor}
                      onChange={(e) => setForm((f) => ({ ...f, minor: e.target.checked, minor_consent: false }))}
                      className="mt-0.5 h-4 w-4 accent-[#F59E0B]"
                    />
                    <span className="block text-sm text-white">{t.booking.minor}</span>
                  </label>
                  {form.minor && (
                    <div className="mt-3 space-y-3" data-testid="booking-minor-panel">
                      <p className="flex items-start gap-2 text-xs leading-relaxed text-amber-200"><AlertCircle size={14} className="mt-0.5 shrink-0" /> {t.booking.minorNotice}</p>
                      <label className="flex cursor-pointer items-start gap-3 text-xs text-slate-200">
                        <input
                          data-testid="booking-checkbox-minor-consent"
                          type="checkbox"
                          required
                          checked={form.minor_consent}
                          onChange={(e) => setForm((f) => ({ ...f, minor_consent: e.target.checked }))}
                          className="mt-0.5 h-4 w-4 accent-[#F59E0B]"
                        />
                        <span>{t.booking.minorConsent} <span className="text-red-300">*</span></span>
                      </label>
                    </div>
                  )}
                </div>
                <div>
                  <label className="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400"><Gift size={11} className="text-gold" /> {t.booking.voucher}</label>
                  <input
                    data-testid="booking-input-voucher"
                    value={form.voucher_code}
                    onChange={(e) => setForm((f) => ({ ...f, voucher_code: e.target.value.toUpperCase() }))}
                    className={`${inputCls} font-mono tracking-[0.2em] ${voucher ? (voucher.valid ? "border-emerald-400/60" : "border-red-400/60") : ""}`}
                    placeholder="CFC-XXXX-XXXX"
                    maxLength={14}
                  />
                  {voucher && (
                    <p data-testid="booking-voucher-status" className={`mt-1.5 flex items-center gap-1.5 text-xs ${voucher.valid ? "text-emerald-300" : "text-red-300"}`}>
                      {voucher.valid ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                      {voucher.valid ? t.booking.voucherOk.replace("{value}", Math.round(voucher.value)) : t.booking.voucherBad[voucher.reason] || t.booking.voucherBad.not_found}
                    </p>
                  )}
                </div>
                <div className="rounded-xl border border-white/10 bg-deep/60 p-4">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      data-testid="booking-checkbox-partner"
                      type="checkbox"
                      checked={form.partner}
                      onChange={(e) => setForm((f) => ({ ...f, partner: e.target.checked }))}
                      className="mt-0.5 h-4 w-4 accent-[#00F0FF]"
                    />
                    <span>
                      <span className="block text-sm text-white">{t.booking.partner}</span>
                      <span className="block text-xs text-slate-500">{t.booking.partnerHint}</span>
                    </span>
                  </label>
                  {form.partner && (
                    <input
                      data-testid="booking-input-partner-name"
                      value={form.partner_name}
                      onChange={set("partner_name")}
                      className={`${inputCls} mt-3`}
                      placeholder={t.booking.partnerName}
                    />
                  )}
                </div>
                <TermsCheckbox checked={terms} onChange={setTerms} testId="booking-terms-checkbox" />
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
