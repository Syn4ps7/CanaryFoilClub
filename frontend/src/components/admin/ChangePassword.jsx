import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { KeyRound, X } from "lucide-react";
import { toast } from "sonner";
import { adminApi, formatApiError } from "@/lib/adminApi";

const inputCls =
  "w-full rounded-xl border border-white/15 bg-deep px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors duration-300 focus:border-glow/70";

const Field = ({ label, testId, ...props }) => (
  <div>
    <label className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{label}</label>
    <input data-testid={testId} type="password" required className={inputCls} {...props} />
  </div>
);

const ChangePassword = ({ open, onClose }) => {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const close = () => {
    setForm({ current: "", next: "", confirm: "" });
    setError("");
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.next.length < 8) return setError("Le nouveau mot de passe doit contenir au moins 8 caractères.");
    if (form.next !== form.confirm) return setError("La confirmation ne correspond pas.");
    setSaving(true);
    try {
      await adminApi.post("/auth/change-password", { current_password: form.current, new_password: form.next });
      toast.success("Mot de passe mis à jour");
      close();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={close} className="fixed inset-0 z-[90] bg-abyss/80 backdrop-blur-sm" />
          <motion.div
            data-testid="change-password-modal"
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="fixed left-1/2 top-1/2 z-[95] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-white/10 bg-panel p-7 sm:p-8"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-glow/90">Sécurité</p>
                <h3 className="mt-2 font-syne text-2xl font-bold">Changer le mot de passe</h3>
              </div>
              <button data-testid="change-password-close" onClick={close} aria-label="Fermer" className="grid h-10 w-10 place-items-center rounded-full border border-white/15 text-slate-300 transition-colors hover:border-glow/60 hover:text-glow">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={submit} className="mt-7 space-y-5">
              <Field label="Mot de passe actuel" testId="password-current" value={form.current} onChange={set("current")} autoComplete="current-password" />
              <Field label="Nouveau mot de passe (8 caractères min.)" testId="password-new" value={form.next} onChange={set("next")} autoComplete="new-password" minLength={8} />
              <Field label="Confirmer le nouveau mot de passe" testId="password-confirm" value={form.confirm} onChange={set("confirm")} autoComplete="new-password" />
              {error && <p data-testid="change-password-error" className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>}
              <motion.button
                data-testid="change-password-submit"
                type="submit"
                disabled={saving}
                whileHover={{ scale: saving ? 1 : 1.02 }}
                whileTap={{ scale: saving ? 1 : 0.97 }}
                className="flex w-full items-center justify-center gap-2 rounded-full bg-glow py-3.5 font-syne text-sm font-bold text-abyss btn-glow disabled:opacity-60"
              >
                <KeyRound size={15} /> {saving ? "Enregistrement…" : "Mettre à jour"}
              </motion.button>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default ChangePassword;
