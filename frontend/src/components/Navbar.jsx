import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X, Waves } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";

const LANGS = ["fr", "en", "es"];

export const scrollToId = (id) => {
  const el = document.querySelector(id);
  if (!el) return;
  if (window.__lenis) {
    window.__lenis.scrollTo(el, { offset: -72, duration: 1.4 });
  } else {
    el.scrollIntoView({ behavior: "smooth" });
  }
};

const Navbar = ({ onBook }) => {
  const { lang, setLang, t } = useLanguage();
  const [open, setOpen] = useState(false);

  const links = [
    { id: "#difference", label: t.nav.difference, testid: "nav-link-difference" },
    { id: "#experiences", label: t.nav.experiences, testid: "nav-link-experiences" },
    { id: "#corporate", label: t.nav.corporate, testid: "nav-link-b2b" },
    { id: "#reseller", label: t.nav.reseller, testid: "nav-link-reseller" },
  ];

  const go = (id) => {
    setOpen(false);
    scrollToId(id);
  };

  const LangSwitch = () => (
    <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
      {LANGS.map((l) => (
        <button
          key={l}
          data-testid={`lang-switcher-${l}`}
          onClick={() => setLang(l)}
          className={`px-3 py-1 rounded-full font-mono text-[11px] uppercase tracking-widest transition-colors duration-300 ${
            lang === l ? "bg-glow text-abyss" : "text-slate-400 hover:text-white"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );

  return (
    <header className="fixed top-0 inset-x-0 z-[80] border-b border-white/10 bg-abyss/60 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-5 sm:px-8 h-[72px] flex items-center justify-between">
        <button
          data-testid="nav-brand-logo"
          onClick={() => go("#hero")}
          className="flex items-center gap-3 group"
        >
          <span className="grid place-items-center h-9 w-9 rounded-full border border-glow/40 text-glow transition-transform duration-500 group-hover:rotate-180">
            <Waves size={16} strokeWidth={1.5} />
          </span>
          <span className="font-syne font-bold tracking-[0.18em] text-sm sm:text-base">
            CANARY <span className="text-glow">FOIL</span> CLUB
          </span>
        </button>

        <nav className="hidden lg:flex items-center gap-8">
          {links.map((l) => (
            <button
              key={l.id}
              data-testid={l.testid}
              onClick={() => go(l.id)}
              className="relative text-sm text-slate-300 hover:text-white transition-colors duration-300 after:absolute after:-bottom-1 after:left-0 after:h-px after:w-0 after:bg-glow after:transition-[width] after:duration-300 hover:after:w-full"
            >
              {l.label}
            </button>
          ))}
        </nav>

        <div className="hidden lg:flex items-center gap-4">
          <LangSwitch />
          <motion.button
            data-testid="nav-book-button"
            onClick={() => onBook()}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            className="rounded-full bg-glow px-6 py-2.5 font-syne text-sm font-bold text-abyss btn-glow"
          >
            {t.nav.book}
          </motion.button>
        </div>

        <button
          data-testid="nav-mobile-menu-button"
          className="lg:hidden text-white"
          onClick={() => setOpen(!open)}
          aria-label="Menu"
        >
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="lg:hidden overflow-hidden border-t border-white/10 bg-panel"
          >
            <div className="px-6 py-6 flex flex-col gap-5">
              {links.map((l) => (
                <button
                  key={l.id}
                  data-testid={`${l.testid}-mobile`}
                  onClick={() => go(l.id)}
                  className="text-left font-syne text-lg text-slate-200"
                >
                  {l.label}
                </button>
              ))}
              <div className="flex items-center justify-between pt-2">
                <LangSwitch />
                <button
                  data-testid="nav-book-button-mobile"
                  onClick={() => {
                    setOpen(false);
                    onBook();
                  }}
                  className="rounded-full bg-glow px-6 py-2.5 font-syne text-sm font-bold text-abyss"
                >
                  {t.nav.book}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Navbar;
