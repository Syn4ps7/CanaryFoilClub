import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Check, ArrowUpRight } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const GEAR_IMG =
  "https://images.unsplash.com/photo-1775317809526-4a8ee9ec310f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwzfHxlZm9pbCUyMHN1cmZib2FyZCUyMG9jZWFuJTIwbHV4dXJ5JTIwZmxpZ2h0fGVufDB8fHx8MTc4ODM3Nzg3OXww&ixlib=rb-4.1.0&q=85";

const Reseller = ({ onBook }) => {
  const { t } = useLanguage();
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const imgY = useTransform(scrollYProgress, [0, 1], [-40, 40]);

  return (
    <section id="reseller" data-testid="reseller-section" ref={ref} className="relative py-28 sm:py-36 bg-deep/40 overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-glow/40 to-transparent" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8 grid items-center gap-14 lg:grid-cols-2">
        <Reveal className="relative order-2 lg:order-1">
          <div className="absolute -inset-3 rounded-[2rem] border border-glow/20 -rotate-2" />
          <div className="relative overflow-hidden rounded-[1.75rem] aspect-[4/5] max-h-[620px] w-full">
            <motion.img
              src={GEAR_IMG}
              alt="Fliteboard eFoil gear on the beach"
              style={{ y: imgY, scale: 1.12 }}
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-abyss/60 via-transparent to-transparent" />
            <span className="absolute bottom-5 left-5 rounded-full bg-abyss/70 backdrop-blur-md border border-white/15 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.25em] text-glow">
              Fliteboard Series 6
            </span>
          </div>
        </Reveal>

        <Reveal delay={0.15} className="order-1 lg:order-2">
          <SectionCaption>{t.reseller.caption}</SectionCaption>
          <span className="inline-block rounded-full border border-glow/40 px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.25em] text-glow">
            {t.reseller.tagline}
          </span>
          <h2 className="mt-6 font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl">
            {t.reseller.title}
          </h2>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400">
            {t.reseller.desc}
          </p>
          <ul className="mt-8 space-y-3.5">
            {t.reseller.points.map((p, i) => (
              <li key={i} className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                <Check size={16} className="mt-1 shrink-0 text-glow" />
                {p}
              </li>
            ))}
          </ul>
          <motion.button
            data-testid="reseller-cta-testdrive-button"
            onClick={() => onBook("testdrive")}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="group mt-10 flex items-center gap-3 rounded-full border border-glow/60 px-8 py-4 font-syne text-sm font-bold text-glow transition-colors duration-300 hover:bg-glow hover:text-abyss"
          >
            {t.reseller.cta}
            <ArrowUpRight size={17} className="transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
          </motion.button>
        </Reveal>
      </div>
    </section>
  );
};

export default Reseller;
