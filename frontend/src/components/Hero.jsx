import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, ChevronDown } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { scrollToId } from "./Navbar";

const HERO_IMG =
  "https://images.unsplash.com/photo-1601869959642-58e1ff8d81a3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwxfHxlZm9pbCUyMHN1cmZib2FyZCUyMG9jZWFuJTIwbHV4dXJ5JTIwZmxpZ2h0fGVufDB8fHx8MTc4ODM3Nzg3OXww&ixlib=rb-4.1.0&q=85";

const MaskedLine = ({ children, delay, className = "" }) => (
  <span className="block overflow-hidden pb-1">
    <motion.span
      initial={{ y: "115%" }}
      animate={{ y: 0 }}
      transition={{ duration: 1.1, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`block ${className}`}
    >
      {children}
    </motion.span>
  </span>
);

const Hero = ({ onBook }) => {
  const { t } = useLanguage();
  const { scrollY } = useScroll();
  const imgY = useTransform(scrollY, [0, 800], [0, 220]);
  const imgScale = useTransform(scrollY, [0, 800], [1.05, 1.2]);
  const fade = useTransform(scrollY, [0, 500], [1, 0]);

  return (
    <section id="hero" data-testid="hero-section" className="relative min-h-screen flex items-end overflow-hidden">
      <motion.div style={{ y: imgY, scale: imgScale }} className="absolute inset-0">
        <img
          src={HERO_IMG}
          alt="eFoil flying over the ocean at Costa Adeje"
          className="h-full w-full object-cover"
        />
      </motion.div>
      <div className="absolute inset-0 bg-gradient-to-b from-abyss/70 via-abyss/30 to-abyss" />
      <div className="absolute inset-0 bg-gradient-to-r from-abyss/70 via-transparent to-transparent" />

      <motion.div style={{ opacity: fade }} className="relative z-10 mx-auto w-full max-w-7xl px-5 sm:px-8 pb-24 pt-44">
        <MaskedLine delay={0.9}>
          <span className="font-mono text-xs sm:text-sm tracking-[0.3em] uppercase text-glow">
            {t.hero.tagline}
          </span>
        </MaskedLine>

        <h1 className="mt-6 font-syne font-extrabold tracking-tight leading-[1.04] text-4xl sm:text-5xl lg:text-6xl max-w-4xl">
          <MaskedLine delay={1.05}>{t.hero.line1}</MaskedLine>
          <MaskedLine delay={1.2} className="text-glow">
            {t.hero.line2}
          </MaskedLine>
          <MaskedLine delay={1.35} className="font-cormorant italic font-medium gold-sheen text-3xl sm:text-4xl lg:text-5xl mt-2">
            {t.hero.line3}
          </MaskedLine>
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 1.6, ease: [0.16, 1, 0.3, 1] }}
          className="mt-6 max-w-xl text-base sm:text-lg leading-relaxed text-slate-300"
        >
          {t.hero.subtitle}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 1.8, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 flex flex-wrap items-center gap-5"
        >
          <motion.button
            data-testid="hero-cta-book-button"
            onClick={() => onBook()}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            className="group flex items-center gap-3 rounded-full bg-glow px-8 py-4 font-syne text-sm sm:text-base font-bold text-abyss btn-glow"
          >
            {t.hero.cta}
            <ArrowRight size={18} className="transition-transform duration-300 group-hover:translate-x-1.5" />
          </motion.button>
          <button
            data-testid="hero-secondary-link"
            onClick={() => scrollToId("#experiences")}
            className="text-sm sm:text-base text-slate-200 underline decoration-glow/60 underline-offset-8 hover:decoration-glow transition-colors"
          >
            {t.hero.secondary}
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 2.1 }}
          className="mt-14 flex flex-wrap gap-x-10 gap-y-3"
        >
          {t.hero.stats.map((s, i) => (
            <span key={i} className="flex items-center gap-3 font-mono text-[11px] sm:text-xs uppercase tracking-[0.2em] text-slate-400">
              <span className="h-1.5 w-1.5 rotate-45 bg-glow" />
              {s}
            </span>
          ))}
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.4, duration: 1 }}
        className="absolute bottom-8 right-8 z-10 hidden sm:flex flex-col items-center gap-2 text-slate-400"
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] [writing-mode:vertical-lr]">
          {t.hero.scroll}
        </span>
        <motion.div animate={{ y: [0, 8, 0] }} transition={{ repeat: Infinity, duration: 1.8 }}>
          <ChevronDown size={16} />
        </motion.div>
      </motion.div>
    </section>
  );
};

export default Hero;
