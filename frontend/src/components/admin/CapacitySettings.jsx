import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Settings2, Check, Clock } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";

const MAX = 6;
const STEP = 90;

const addMinutes = (t, n) => {
  const [h, m] = t.split(":").map(Number);
  const total = Math.min(h * 60 + m + n, 23 * 60 + 30);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
};

const fitTimes = (times, n) => {
  const out = times.slice(0, n);
  while (out.length < n) out.push(addMinutes(out[out.length - 1] || "07:30", STEP));
  return out;
};

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
  const [form, setForm] = useState({ boards: 3, slots_per_day: 6, slot_times: [] });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setForm({ boards: settings.boards, slots_per_day: settings.slots_per_day, slot_times: settings.slot_times });
  }, [settings]);

  const dirty = settings && JSON.stringify(form) !== JSON.stringify({ boards: settings.boards, slots_per_day: settings.slots_per_day, slot_times: settings.slot_times });

  const setSlots = (n) => setForm((f) => ({ ...f, slots_per_day: n, slot_times: fitTimes(f.slot_times, n) }));
  const setTime = (i, v) => setForm((f) => ({ ...f, slot_times: f.slot_times.map((t, j) => (j === i ? v : t)) }));

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
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-400">Capacité & horaires</p>
        <Settings2 size={15} className="text-glow" />
      </div>
      <div className="mt-5 space-y-4">
        <Stepper label="Planches actives" value={form.boards} onChange={(v) => setForm((f) => ({ ...f, boards: v }))} testId="settings-boards" />
        <Stepper label="Créneaux / jour (max 6)" value={form.slots_per_day} onChange={setSlots} testId="settings-slots" />
      </div>

      <div className="mt-5 border-t border-white/10 pt-4">
        <p className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500"><Clock size={11} /> Heure de chaque créneau</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {form.slot_times.map((t, i) => (
            <label key={i} className="flex items-center gap-2 rounded-xl border border-white/10 bg-deep px-2.5 py-1.5">
              <span className="font-mono text-[10px] text-slate-500">C{i + 1}</span>
              <input
                data-testid={`settings-slot-time-${i + 1}`}
                type="time"
                value={t}
                step={900}
                onChange={(e) => e.target.value && setTime(i, e.target.value)}
                className="w-full bg-transparent font-outfit text-sm tabular-nums text-white outline-none"
              />
            </label>
          ))}
        </div>
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
