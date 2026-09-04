import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, ScrollText } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { TERMS } from "@/i18n/terms";

const TermsModal = ({ open, onClose }) => {
  const { lang } = useLanguage();
  const t = TERMS[lang] || TERMS.fr;

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-[90] bg-abyss/85 backdrop-blur-sm" />
          <motion.div
            data-testid="terms-modal"
            data-lenis-prevent
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 30 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="fixed left-1/2 top-1/2 z-[95] flex max-h-[88vh] w-[calc(100%-1.5rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-3xl border border-white/10 bg-panel"
          >
            <div className="flex items-start justify-between gap-4 border-b border-white/10 p-6 sm:p-8">
              <div>
                <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90"><ScrollText size={12} /> {t.subtitle}</p>
                <h2 className="mt-2 font-syne text-2xl sm:text-3xl font-bold" data-testid="terms-title">{t.title}</h2>
              </div>
              <button data-testid="terms-close" onClick={onClose} aria-label="Close" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow">
                <X size={18} />
              </button>
            </div>
            <div className="overflow-y-auto p-6 sm:p-8 space-y-7" data-testid="terms-content">
              {t.sections.map((s) => (
                <section key={s.h}>
                  <h3 className="font-syne text-base font-bold text-white">{s.h}</h3>
                  {s.p.map((p, i) => (
                    <p key={i} className="mt-2 text-sm leading-relaxed text-slate-300">{p}</p>
                  ))}
                </section>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default TermsModal;
