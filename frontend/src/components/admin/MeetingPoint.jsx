import { useEffect, useState } from "react";
import { toast } from "sonner";
import { MapPin, Send, RotateCcw } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";

const inputCls = "rounded-xl border border-white/15 bg-deep px-3 py-2 text-sm text-white outline-none transition-colors focus:border-glow/70";

const MeetingPoint = ({ day }) => {
  const [mp, setMp] = useState(null);
  const [spot, setSpot] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () =>
    adminApi
      .get("/admin/planning/meeting-point", { params: { day } })
      .then(({ data }) => {
        setMp(data);
        setSpot(data.spot);
        setAddress(data.address);
      })
      .catch(() => setMp(null));

  useEffect(() => {
    setMp(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day]);

  const save = async (reset = false) => {
    setSaving(true);
    try {
      await adminApi.put("/admin/planning/meeting-point", reset ? { date: day, spot: null } : { date: day, spot, address });
      toast.success(reset ? "Retour à la recommandation météo" : "Point de rendez-vous enregistré");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  if (!mp) return null;
  const dirty = spot !== mp.spot || address !== mp.address;
  const options = mp.options.some((o) => o.spot === spot) ? mp.options : [...mp.options, { spot, address }];

  return (
    <div className="mt-5 rounded-xl border border-gold/25 bg-gold/5 p-4" data-testid="meeting-point">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-gold">
          <MapPin size={11} /> Point de RDV envoyé aux clients
        </p>
        <span data-testid="meeting-point-source" className="rounded-full border border-white/15 px-2.5 py-0.5 text-[10px] text-slate-400">
          {mp.source === "override" ? "Choix manuel" : mp.source === "weather" ? "Recommandation météo" : "Par défaut"}
        </span>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-[220px_1fr_auto]">
        <select data-testid="meeting-point-spot" value={spot} onChange={(e) => { setSpot(e.target.value); const o = mp.options.find((x) => x.spot === e.target.value); if (o) setAddress(o.address); }} className={inputCls} style={{ backgroundColor: "#0A1322" }}>
          {options.map((o) => <option key={o.spot} value={o.spot}>{o.spot}</option>)}
        </select>
        <input data-testid="meeting-point-address" value={address} onChange={(e) => setAddress(e.target.value)} className={inputCls} placeholder="Accès / parking / repère" />
        <div className="flex gap-2">
          <button data-testid="meeting-point-save" onClick={() => save(false)} disabled={!dirty || saving} className="inline-flex items-center gap-1.5 rounded-xl border border-gold/50 bg-gold/15 px-3 py-2 text-xs font-semibold text-gold transition-colors hover:bg-gold/25 disabled:opacity-40">
            <Send size={12} /> Enregistrer
          </button>
          {mp.source === "override" && (
            <button data-testid="meeting-point-reset" onClick={() => save(true)} disabled={saving} title="Revenir à la recommandation météo" className="grid h-9 w-9 place-items-center rounded-xl border border-white/15 text-slate-400 transition-colors hover:text-white">
              <RotateCcw size={13} />
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 text-[11px] text-slate-500">
        Rappel automatique envoyé la veille à partir de {mp.reminder_hour}h (heure des Canaries) à chaque client confirmé, avec ce point de rendez-vous, l'heure du créneau et les conditions prévues.
      </p>
    </div>
  );
};

export default MeetingPoint;
