import { motion } from "framer-motion";
import { Zap, Radio, Navigation } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const ICONS = [Zap, Radio, Navigation];

const Pillars = () => {
  const { t } = useLanguage();

  return (
    <section id="difference" data-testid="pillars-section" className="relative py-28 sm:py-36">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionCaption>{t.pillars.caption}</SectionCaption>
          <h2 className="font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl max-w-2xl">
            {t.pillars.title}
          </h2>
          <p className="mt-4 max-w-xl text-base text-slate-400 leading-relaxed">{t.pillars.sub}</p>
        </Reveal>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {t.pillars.items.map((item, i) => {
            const Icon = ICONS[i];
            return (
              <motion.article
                key={i}
                data-testid={`pillar-card-${i}`}
                initial={{ opacity: 0, y: 48 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.9, delay: i * 0.15, ease: [0.16, 1, 0.3, 1] }}
                whileHover={{ y: -8 }}
                className="group relative glass rounded-2xl p-8 overflow-hidden transition-[border-color,box-shadow] duration-500 hover:border-glow/40 hover:shadow-[0_0_60px_rgba(0,240,255,0.12)]"
              >
                <span className="pointer-events-none absolute -top-6 right-2 font-syne text-[7rem] font-extrabold leading-none text-white/5 select-none">
                  0{i + 1}
                </span>
                <div className="relative">
                  <span className="inline-grid place-items-center h-12 w-12 rounded-full border border-glow/30 bg-glow/10 text-glow transition-transform duration-500 group-hover:scale-110">
                    <Icon size={20} strokeWidth={1.5} />
                  </span>
                  <h3 className="mt-6 font-syne text-xl sm:text-2xl font-semibold leading-snug">
                    {item.title}
                  </h3>
                  <p className="mt-4 text-sm sm:text-base leading-relaxed text-slate-400">
                    {item.desc}
                  </p>
                </div>
                <span className="absolute bottom-0 left-0 h-px w-0 bg-gradient-to-r from-glow to-transparent transition-[width] duration-700 group-hover:w-full" />
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Pillars;
