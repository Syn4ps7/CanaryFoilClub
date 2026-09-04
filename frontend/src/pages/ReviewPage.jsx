import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Star, Send, CheckCircle2 } from "lucide-react";
import { LanguageProvider, useLanguage } from "@/i18n/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const ReviewForm = ({ token, ctx, onDone }) => {
  const { t } = useLanguage();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const s = t.reviewPage;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!rating) return setError(s.rating);
    setSaving(true);
    try {
      const r = await fetch(`${API}/reviews/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comment, display_name: name || undefined }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || "error");
      onDone();
    } catch (err) {
      setError(typeof err.message === "string" ? err.message : "Erreur");
    } finally {
      setSaving(false);
    }
  };

  const shown = hover || rating;
  return (
    <form onSubmit={submit} className="mt-8 space-y-6" data-testid="review-form">
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{s.rating}</p>
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <button
              key={i}
              type="button"
              data-testid={`review-star-${i}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(0)}
              onClick={() => setRating(i)}
              className="transition-transform hover:scale-110"
              aria-label={`${i}/5`}
            >
              <Star size={34} className={i <= shown ? "fill-gold text-gold drop-shadow-[0_0_10px_rgba(212,175,55,0.5)]" : "text-white/20"} />
            </button>
          ))}
          <span className="ml-2 font-cormorant text-lg italic text-slate-300" data-testid="review-star-label">{shown ? s.stars[shown - 1] : ""}</span>
        </div>
      </div>
      <div>
        <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{s.comment}</label>
        <textarea data-testid="review-comment" required minLength={3} maxLength={800} rows={5} value={comment} onChange={(e) => setComment(e.target.value)} className={`${inputCls} resize-none`} placeholder={s.commentPlaceholder} />
      </div>
      <div>
        <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{s.name}</label>
        <input data-testid="review-name" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder={ctx.name} />
      </div>
      {error && <p data-testid="review-error" className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>}
      <motion.button
        data-testid="review-submit"
        type="submit"
        disabled={saving}
        whileHover={{ scale: saving ? 1 : 1.02 }}
        whileTap={{ scale: saving ? 1 : 0.97 }}
        className="flex w-full items-center justify-center gap-2 rounded-full bg-glow py-4 font-syne text-sm font-bold text-abyss btn-glow disabled:opacity-60"
      >
        <Send size={15} /> {s.submit}
      </motion.button>
    </form>
  );
};

const ReviewInner = () => {
  const { token } = useParams();
  const { t, setLang } = useLanguage();
  const [ctx, setCtx] = useState(null);
  const [state, setState] = useState("loading");

  useEffect(() => {
    document.title = "Avis — Canary Foil Club";
    fetch(`${API}/reviews/${token}`)
      .then(async (r) => {
        if (!r.ok) throw new Error();
        const data = await r.json();
        setCtx(data);
        if (["fr", "en", "es"].includes(data.lang)) setLang(data.lang);
        setState(data.already_reviewed ? "already" : "form");
      })
      .catch(() => setState("invalid"));
  }, [token, setLang]);

  const s = t.reviewPage;
  return (
    <div className="min-h-screen bg-abyss noise-overlay flex items-center justify-center px-5 py-16 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-glow/10 blur-[140px]" />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-xl rounded-3xl border border-white/10 bg-panel/80 backdrop-blur-xl p-8 sm:p-10"
        data-testid="review-page"
      >
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Canary <span className="text-white">Foil</span> Club — {s.caption}</p>
        {state === "loading" && <div className="mt-8 h-8 w-8 rounded-full border-2 border-glow/30 border-t-glow animate-spin" />}
        {state === "invalid" && <p data-testid="review-invalid" className="mt-6 text-slate-300">{s.invalid}</p>}
        {state === "already" && (
          <div data-testid="review-already" className="mt-6 flex items-start gap-3 text-slate-200"><CheckCircle2 className="text-glow shrink-0" /> {s.already}</div>
        )}
        {state === "done" && (
          <div data-testid="review-thanks" className="mt-6">
            <CheckCircle2 size={40} className="text-glow" />
            <h1 className="mt-4 font-syne text-2xl sm:text-3xl font-extrabold">{s.thanks}</h1>
            <p className="mt-2 text-slate-400">{s.thanksSub}</p>
          </div>
        )}
        {state === "form" && ctx && (
          <>
            <h1 className="mt-4 font-syne text-2xl sm:text-3xl font-extrabold tracking-tight">{s.title.replace("{name}", ctx.name)}</h1>
            <p className="mt-3 text-sm text-slate-400">{s.intro}</p>
            <ReviewForm token={token} ctx={ctx} onDone={() => setState("done")} />
          </>
        )}
        <a href="/" className="mt-8 inline-block text-xs text-slate-500 transition-colors hover:text-glow" data-testid="review-back">← {s.back}</a>
      </motion.div>
    </div>
  );
};

export default function ReviewPage() {
  return (
    <LanguageProvider>
      <ReviewInner />
    </LanguageProvider>
  );
}
