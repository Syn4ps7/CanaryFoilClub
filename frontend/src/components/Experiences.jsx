import { motion } from "framer-motion";
import { Check, Clock, ArrowUpRight } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const TESTIDS = {
  discovery: "card-experience-discovery",
  duo: "card-experience-duo",
  drone: "card-experience-drone",
};

const Experiences = ({ onBook }) => {
  const { t } = useLanguage();

  return (
    <section id="experiences" data-testid="experiences-section" className="relative py-28 sm:py-36 bg-deep/40">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-glow/40 to-transparent" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal className="flex flex-col items-start">
          <SectionCaption>{t.experiences.caption}</SectionCaption>
          <h2 className="font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl">
            {t.experiences.title}
          </h2>
          <p className="mt-4 max-w-xl text-base text-slate-400 leading-relaxed">
            {t.experiences.sub}
          </p>
        </Reveal>

        <div className="mt-16 grid gap-6 lg:grid-cols-3">
          {t.experiences.cards.map((card, i) => {
            const featured = card.id === "duo";
            return (
              <motion.article
                key={card.id}
                data-testid={TESTIDS[card.id]}
                initial={{ opacity: 0, y: 48 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.9, delay: i * 0.15, ease: [0.16, 1, 0.3, 1] }}
                whileHover={{ y: -8 }}
                className={`relative flex flex-col rounded-2xl p-8 transition-[box-shadow,border-color] duration-500 ${
                  featured
                    ? "bg-panel border border-gold/50 shadow-[0_0_80px_rgba(212,175,55,0.12)] hover:shadow-[0_0_100px_rgba(212,175,55,0.22)]"
                    : "glass hover:border-glow/40 hover:shadow-[0_0_60px_rgba(0,240,255,0.1)]"
                }`}
              >
                <span
                  className={`self-start rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] ${
                    featured ? "border-gold/60 text-gold" : "border-glow/40 text-glow"
                  }`}
                >
                  {card.badge}
                </span>

                <h3 className="mt-6 font-syne text-xl sm:text-2xl font-semibold">{card.name}</h3>

                <div className="mt-4 flex items-end gap-3">
                  <span className={`font-cormorant text-5xl sm:text-6xl font-semibold leading-none ${featured ? "gold-sheen" : "text-white"}`}>
                    {card.price}
                  </span>
                  <span className="pb-1 font-mono text-[10px] uppercase tracking-widest text-slate-500">
                    {t.experiences.from}
                  </span>
                </div>

                <p className="mt-3 flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-slate-400">
                  <Clock size={13} className="text-glow" />
                  {card.duration}
                </p>

                <ul className="mt-8 flex-1 space-y-3.5">
                  {card.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm leading-relaxed text-slate-300">
                      <Check size={15} className={`mt-0.5 shrink-0 ${featured ? "text-gold" : "text-glow"}`} />
                      {f}
                    </li>
                  ))}
                </ul>

                <motion.button
                  data-testid={`book-${card.id}-button`}
                  onClick={() => onBook(card.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  className={`group mt-10 flex w-full items-center justify-center gap-2 rounded-full py-3.5 font-syne text-sm font-bold transition-colors duration-300 ${
                    featured
                      ? "bg-gold text-abyss hover:bg-[#e5c65a]"
                      : "border border-glow/50 text-glow hover:bg-glow hover:text-abyss"
                  }`}
                >
                  {t.experiences.book}
                  <ArrowUpRight size={16} className="transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </motion.button>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Experiences;
