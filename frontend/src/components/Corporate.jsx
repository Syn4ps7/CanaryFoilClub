import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Check, Users, ArrowUpRight } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const SUNSET_IMG =
  "https://images.unsplash.com/photo-1609601521638-4c91a255208f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w8NjA1NTJ8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjB5YWNodCUyMHN1bnNldCUyMG9jZWFuJTIwY2hhbXBhZ25lfGVufDB8fHx8MTc4ODM3Nzg4OHww&ixlib=rb-4.1.0&q=85";

const Corporate = ({ onBook }) => {
  const { t } = useLanguage();
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const imgY = useTransform(scrollYProgress, [0, 1], [-40, 40]);

  return (
    <section id="corporate" data-testid="corporate-section" ref={ref} className="relative py-28 sm:py-36 overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(212,175,55,0.07),transparent_55%)]" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8 grid items-center gap-14 lg:grid-cols-2">
        <Reveal>
          <SectionCaption>{t.corporate.caption}</SectionCaption>
          <span className="inline-block rounded-full border border-gold/50 px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.25em] text-gold">
            {t.corporate.badge}
          </span>
          <h2 className="mt-6 font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl">
            {t.corporate.title}
          </h2>
          <div className="mt-5 flex items-end gap-4">
            <span className="font-cormorant text-5xl sm:text-6xl font-semibold leading-none gold-sheen">
              {t.corporate.price}
            </span>
            <span className="pb-1.5 flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-slate-400">
              <Users size={14} className="text-gold" />
              {t.corporate.capacity}
            </span>
          </div>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400">
            {t.corporate.desc}
          </p>
          <ul className="mt-8 space-y-3.5">
            {t.corporate.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                <Check size={16} className="mt-1 shrink-0 text-gold" />
                {h}
              </li>
            ))}
          </ul>
          <motion.button
            data-testid="b2b-cta-reserve-button"
            onClick={() => onBook("corporate")}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="group mt-10 flex items-center gap-3 rounded-full bg-gold px-8 py-4 font-syne text-sm font-bold text-abyss"
          >
            {t.corporate.cta}
            <ArrowUpRight size={17} className="transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
          </motion.button>
        </Reveal>

        <Reveal delay={0.15} className="relative">
          <div className="absolute -inset-3 rounded-[2rem] border border-gold/25 rotate-2" />
          <div className="relative overflow-hidden rounded-[1.75rem] aspect-[4/5] max-h-[620px] w-full">
            <motion.img
              src={SUNSET_IMG}
              alt="Champagne at sunset on the Costa Adeje coast"
              style={{ y: imgY, scale: 1.12 }}
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-abyss/60 via-transparent to-transparent" />
          </div>
        </Reveal>
      </div>
    </section>
  );
};

export default Corporate;
