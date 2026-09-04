import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, ShieldCheck } from "lucide-react";
import { LanguageProvider, useLanguage } from "@/i18n/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Inner = () => {
  const [params] = useSearchParams();
  const { t } = useLanguage();
  const sessionId = params.get("session_id");
  const cancelled = params.get("cancelled");
  const [state, setState] = useState(cancelled ? "cancelled" : "checking");
  const [kind, setKind] = useState(null);
  const attempts = useRef(0);

  useEffect(() => {
    document.title = "Paiement — Canary Foil Club";
    if (!sessionId) return;
    let timer;
    const poll = async () => {
      attempts.current += 1;
      try {
        const r = await fetch(`${API}/payments/status/${sessionId}`);
        if (!r.ok) throw new Error();
        const d = await r.json();
        setKind(d.kind);
        if (d.payment_status === "paid") return setState("success");
        if (["failed", "expired", "refunded"].includes(d.payment_status)) return setState("failed");
      } catch {
        if (attempts.current >= 3) return setState("failed");
      }
      if (attempts.current >= 10) return setState("pending");
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => clearTimeout(timer);
  }, [sessionId]);

  const p = t.payment;
  const view = {
    checking: { icon: <Loader2 size={40} className="animate-spin text-glow" />, title: p.checking, sub: "" },
    pending: { icon: <Loader2 size={40} className="animate-spin text-glow" />, title: p.pending, sub: "" },
    success: { icon: <CheckCircle2 size={44} className="text-glow" />, title: kind === "voucher" ? p.successVoucher : p.successBooking, sub: p.successSub },
    failed: { icon: <XCircle size={44} className="text-red-400" />, title: p.failed, sub: "" },
    cancelled: { icon: <XCircle size={44} className="text-amber-300" />, title: p.cancelled, sub: "" },
  }[state];

  return (
    <div className="min-h-screen bg-abyss noise-overlay flex items-center justify-center px-5 py-16 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-glow/10 blur-[140px]" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }} data-testid="payment-page" data-state={state}
        className="relative w-full max-w-lg rounded-3xl border border-white/10 bg-panel/80 backdrop-blur-xl p-8 sm:p-10 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Canary <span className="text-white">Foil</span> Club</p>
        <div className="mt-8 flex justify-center">{view.icon}</div>
        <h1 data-testid="payment-title" className="mt-5 font-syne text-2xl sm:text-3xl font-extrabold tracking-tight">{view.title}</h1>
        {view.sub && <p className="mt-3 text-sm text-slate-400">{view.sub}</p>}
        <p className="mt-6 inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500"><ShieldCheck size={12} /> {p.secure}</p>
        <div className="mt-8">
          <a href="/" data-testid="payment-back" className="inline-flex items-center justify-center rounded-full border border-white/15 px-6 py-3 text-sm text-slate-200 transition-colors hover:border-glow hover:text-glow">← {p.back}</a>
        </div>
      </motion.div>
    </div>
  );
};

export default function PaymentPage() {
  return (
    <LanguageProvider>
      <Inner />
    </LanguageProvider>
  );
}
