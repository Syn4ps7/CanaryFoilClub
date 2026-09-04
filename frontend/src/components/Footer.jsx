import { useState } from "react";
import { MessageCircle, Instagram, MapPin, ShieldCheck } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import TermsModal from "./TermsModal";
import { Reveal } from "./Reveal";

const Footer = () => {
  const { t } = useLanguage();
  const [terms, setTerms] = useState(false);

  return (
    <footer data-testid="site-footer" className="relative border-t border-white/10 bg-abyss pt-20 pb-10 overflow-hidden">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <div className="grid gap-12 md:grid-cols-3">
            <div>
              <p className="font-syne font-bold tracking-[0.18em] text-lg">
                CANARY <span className="text-glow">FOIL</span> CLUB
              </p>
              <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-400">
                {t.footer.tagline}
              </p>
            </div>

            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-500">{t.footer.contact}</p>
              <div className="mt-5 space-y-3.5">
                <a
                  data-testid="footer-whatsapp-link"
                  href="https://wa.me/34600000000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 text-sm text-slate-300 transition-colors hover:text-glow"
                >
                  <MessageCircle size={16} className="text-glow" />
                  +34 600 000 000 — WhatsApp VIP
                </a>
                <a
                  data-testid="footer-instagram-link"
                  href="https://instagram.com/canaryfoilclub"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 text-sm text-slate-300 transition-colors hover:text-glow"
                >
                  <Instagram size={16} className="text-glow" />
                  @canaryfoilclub
                </a>
                <p className="flex items-center gap-3 text-sm text-slate-400">
                  <MapPin size={16} className="text-glow" />
                  {t.footer.location}
                </p>
              </div>
            </div>

            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-500">{t.footer.payments}</p>
              <div className="mt-5 flex flex-wrap items-center gap-2.5">
                {["Stripe", "VISA", "Mastercard", "Apple Pay"].map((p) => (
                  <span
                    key={p}
                    data-testid={`payment-badge-${p.toLowerCase().replace(" ", "-")}`}
                    className="rounded-lg border border-white/15 bg-panel px-3.5 py-1.5 font-mono text-[11px] tracking-wider text-slate-300"
                  >
                    {p}
                  </span>
                ))}
              </div>
              <p className="mt-5 flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck size={14} className="text-glow" />
                SSL · 3-D Secure
              </p>
            </div>
          </div>
        </Reveal>

        <p className="pointer-events-none mt-16 select-none text-center font-syne text-[13vw] leading-none font-extrabold text-stroke-faint">
          FOIL CLUB
        </p>

        <p className="mt-8 border-t border-white/10 pt-6 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-slate-600">
          © 2026 Canary Foil Club ·{" "}
          <button data-testid="footer-terms-link" onClick={() => setTerms(true)} className="underline-offset-4 transition-colors hover:text-glow hover:underline">
            {t.footer.terms}
          </button>
        </p>
      </div>
      <TermsModal open={terms} onClose={() => setTerms(false)} />
    </footer>
  );
};

export default Footer;
