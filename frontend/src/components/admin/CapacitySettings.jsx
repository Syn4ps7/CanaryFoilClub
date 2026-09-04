import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Settings2, Check } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";

const MAX = 6;

const Stepper = ({ label, value, onChange, testId }) => (
  <div className="flex items-center justify-between gap-3">
    <span className="text-xs text-slate-300">{label}</span>
    <div className="inline-flex items-center rounded-full border border-white/15 bg-deep">
      <button type="button" data-testid={`${testId}-minus`} onClick={() => onChange(Math.max(1, value - 1))} className="h-8 w-8 text-slate-300 transition-colors hover:text-glow">−</button>
      <span data-testid={`${testId}-value`} className="w-8 text-center font-outfit text-sm font-semibold tabular-nums text-white">{value}</span>
      <button type="button" data-testid={`${testId}-plus`} onClick={() => onChange(Math.min(MAX, value + 1))} className="h-8 w-8 text-slate-300 transition-colors hover:text-glow">+</button>
    </div>
  </div>
);

const CapacitySettings = ({ settings, onSaved }) => {
  const [form, setForm] = useState({ boards: 3, slots_per_day: 6 });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setForm({ boards: settings.boards, slots_per_day: settings.slots_per_day });
  }, [settings]);

  const dirty = settings && (form.boards !== settings.boards || form.slots_per_day !== settings.slots_per_day);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await adminApi.put("/admin/settings", form);
      toast.success(`Capacité mise à jour : ${data.boards} planches × ${data.slots_per_day} créneaux`);
      onSaved(data);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.28, ease: [0.16, 1, 0.3, 1] }}
      data-testid="capacity-settings"
      className="rounded-2xl border border-white/10 bg-panel/70 p-5 sm:p-6 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Capacité du jour</p>
        <Settings2 size={15} className="text-glow" />
      </div>
      <div className="mt-5 space-y-4">
        <Stepper label="Planches actives" value={form.boards} onChange={(v) => setForm((f) => ({ ...f, boards: v }))} testId="settings-boards" />
        <Stepper label="Créneaux / jour (max 6)" value={form.slots_per_day} onChange={(v) => setForm((f) => ({ ...f, slots_per_day: v }))} testId="settings-slots" />
      </div>
      <p className="mt-4 text-xs text-slate-500">
        Capacité = <span className="text-white">{form.boards} × {form.slots_per_day} = {form.boards * form.slots_per_day}</span> sessions-planche / jour
      </p>
      <button
        data-testid="settings-save"
        onClick={save}
        disabled={!dirty || saving}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full border border-glow/40 bg-glow/10 py-2.5 text-xs font-semibold text-glow transition-colors hover:bg-glow/20 disabled:opacity-40"
      >
        <Check size={14} /> {saving ? "Enregistrement…" : "Appliquer"}
      </button>
    </motion.div>
  );
};

export default CapacitySettings;
