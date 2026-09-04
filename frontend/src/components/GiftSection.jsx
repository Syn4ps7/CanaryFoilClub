import { motion } from "framer-motion";
import { Gift, Check, ArrowUpRight } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const GiftSection = ({ onGift }) => {
  const { t } = useLanguage();
  return (
    <section id="gift" data-testid="gift-section" className="relative py-24 sm:py-32 overflow-hidden">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-[2rem] border border-gold/30 bg-panel/60 backdrop-blur-xl p-8 sm:p-12 lg:p-16">
            <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gold/15 blur-[100px]" />
            <div className="pointer-events-none absolute -left-16 bottom-0 h-56 w-56 rounded-full bg-glow/10 blur-[90px]" />
            <div className="relative grid items-center gap-10 lg:grid-cols-[1.2fr_1fr]">
              <div>
                <SectionCaption>{t.gift.caption}</SectionCaption>
                <h2 className="font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl">{t.gift.title}</h2>
                <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-400">{t.gift.desc}</p>
                <ul className="mt-7 flex flex-wrap gap-x-8 gap-y-3">
                  {t.gift.points.map((p, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                      <Check size={15} className="text-gold" /> {p}
                    </li>
                  ))}
                </ul>
                <motion.button
                  data-testid="gift-cta-button"
                  onClick={onGift}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="group mt-10 inline-flex items-center gap-3 rounded-full bg-gold px-8 py-4 font-syne text-sm font-bold text-abyss"
                >
                  <Gift size={17} />
                  {t.gift.cta}
                  <ArrowUpRight size={17} className="transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
                </motion.button>
              </div>
              <motion.div
                initial={{ rotate: -4, opacity: 0, y: 20 }}
                whileInView={{ rotate: -2, opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                className="relative mx-auto w-full max-w-sm rounded-2xl border border-gold/40 bg-abyss p-7 shadow-[0_30px_80px_rgba(0,0,0,0.5)]"
                data-testid="gift-card-preview"
              >
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-gold">Gift voucher</p>
                  <Gift size={18} className="text-gold" />
                </div>
                <p className="mt-8 font-syne text-xl font-extrabold tracking-tight">
                  CANARY <span className="text-glow">FOIL</span> CLUB
                </p>
                <p className="mt-1 font-cormorant text-lg italic text-slate-300">Discovery Session · Costa Adeje</p>
                <p className="mt-8 rounded-xl border border-dashed border-gold/50 bg-panel/80 px-4 py-3 text-center font-mono text-lg tracking-[0.3em] text-white">CFC-XXXX-XXXX</p>
                <div className="mt-6 flex items-end justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">Valid 12 months</span>
                  <span className="font-outfit text-3xl font-semibold tabular-nums gold-sheen">145 €</span>
                </div>
              </motion.div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
};

export default GiftSection;
