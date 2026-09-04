import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Star, Quote } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const EXP = {
  fr: { discovery: "Discovery Session", duo: "Duo VIP", drone: "Option Drone", corporate: "Corporate Sunset", testdrive: "Test Drive" },
  en: { discovery: "Discovery Session", duo: "Duo VIP", drone: "Drone Option", corporate: "Corporate Sunset", testdrive: "Test Drive" },
  es: { discovery: "Discovery Session", duo: "Duo VIP", drone: "Opción Drone", corporate: "Corporate Sunset", testdrive: "Test Drive" },
};

export const Stars = ({ value, size = 14, className = "" }) => (
  <span className={`inline-flex gap-0.5 ${className}`} aria-label={`${value}/5`}>
    {[1, 2, 3, 4, 5].map((i) => (
      <Star key={i} size={size} className={i <= value ? "fill-gold text-gold" : "text-white/20"} />
    ))}
  </span>
);

const Testimonials = () => {
  const { t, lang } = useLanguage();
  const [reviews, setReviews] = useState([]);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/reviews?limit=9`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setReviews)
      .catch(() => setReviews([]));
  }, []);

  if (!reviews.length) return null;
  const avg = (reviews.reduce((a, r) => a + r.rating, 0) / reviews.length).toFixed(1);

  return (
    <section id="reviews" data-testid="reviews-section" className="relative py-28 sm:py-36 overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(0,240,255,0.06),transparent_55%)]" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionCaption>{t.reviews.caption}</SectionCaption>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <h2 className="font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl max-w-xl">{t.reviews.title}</h2>
            <div className="flex items-center gap-3" data-testid="reviews-average">
              <span className="font-outfit text-5xl font-semibold tabular-nums gold-sheen">{avg}</span>
              <div>
                <Stars value={Math.round(avg)} size={16} />
                <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{reviews.length} · {t.reviews.subtitle}</p>
              </div>
            </div>
          </div>
        </Reveal>
        <div className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {reviews.map((r, i) => (
            <Reveal key={r.id} delay={0.08 * (i % 3)}>
              <motion.article
                whileHover={{ y: -6 }}
                transition={{ duration: 0.35 }}
                data-testid={`review-card-${r.id}`}
                className={`relative h-full rounded-3xl border p-7 backdrop-blur-xl ${r.featured ? "border-gold/40 bg-gold/5" : "border-white/10 bg-panel/60"}`}
              >
                <Quote size={28} className="absolute right-6 top-6 text-glow/20" />
                <Stars value={r.rating} />
                <p className="mt-5 font-cormorant text-xl leading-relaxed text-slate-100 italic">« {r.comment} »</p>
                {r.reply && (
                  <div className="mt-4 rounded-xl border-l-2 border-glow/60 bg-glow/5 px-4 py-3" data-testid={`review-reply-${r.id}`}>
                    <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-glow/80">{t.reviews.reply}</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">{r.reply}</p>
                  </div>
                )}
                <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
                  <div>
                    <p className="font-syne text-sm font-bold">{r.name}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">{EXP[lang]?.[r.experience] || r.experience}</p>
                  </div>
                  <p className="font-mono text-[10px] text-slate-500">{new Date(r.date).toLocaleDateString(lang === "en" ? "en-GB" : lang === "es" ? "es-ES" : "fr-FR", { month: "short", year: "numeric" })}</p>
                </div>
              </motion.article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
