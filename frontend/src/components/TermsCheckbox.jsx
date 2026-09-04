import { useState } from "react";
import { useLanguage } from "@/i18n/LanguageContext";
import TermsModal from "./TermsModal";

const TermsCheckbox = ({ checked, onChange, testId = "terms-checkbox", accent = "#00F0FF" }) => {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-white/10 bg-deep/60 px-4 py-3">
      <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-200">
        <input
          data-testid={testId}
          type="checkbox"
          required
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0"
          style={{ accentColor: accent }}
        />
        <span>
          {t.footer.acceptTerms}{" "}
          <button type="button" data-testid={`${testId}-link`} onClick={() => setOpen(true)} className="underline decoration-dotted underline-offset-4 transition-colors hover:text-glow" style={{ color: accent }}>
            {t.footer.termsShort}
          </button>
          <span className="text-red-300"> *</span>
        </span>
      </label>
      <TermsModal open={open} onClose={() => setOpen(false)} />
    </div>
  );
};

export default TermsCheckbox;
