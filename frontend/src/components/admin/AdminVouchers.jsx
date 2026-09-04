import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Gift, Copy, Mail, CheckCircle2, Ban, RotateCcw, FileDown } from "lucide-react";
import { adminApi, eur, formatApiError } from "@/lib/adminApi";
import { EXP_LABELS } from "@/components/admin/BookingsTable";

const STATUS = {
  pending: { label: "En attente de paiement", cls: "border-amber-400/40 bg-amber-400/10 text-amber-300" },
  paid: { label: "Actif", cls: "border-glow/40 bg-glow/10 text-glow" },
  redeemed: { label: "Utilisé", cls: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300" },
  cancelled: { label: "Annulé", cls: "border-red-400/40 bg-red-400/10 text-red-300" },
};

const fmt = (d) => (d ? new Date(d).toLocaleDateString("fr-FR") : "—");

const AdminVouchers = ({ onLogout }) => {
  const [vouchers, setVouchers] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await adminApi.get("/admin/vouchers");
      setVouchers(data);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, fn, msg) => {
    setBusy(id);
    try {
      await fn();
      toast.success(msg);
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(null);
    }
  };
  const setStatus = (v, status, msg) => act(v.id, () => adminApi.patch(`/admin/vouchers/${v.id}`, { status }), msg);
  const resend = (v) => act(v.id, () => adminApi.post(`/admin/vouchers/${v.id}/resend`), "Bon cadeau renvoyé par email");
  const copy = (code) => navigator.clipboard?.writeText(code).then(() => toast.success("Code copié"));
  const downloadPdf = async (v) => {
    try {
      const res = await adminApi.get(`/admin/vouchers/${v.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bon-cadeau-${v.code}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF téléchargé");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const sum = (st) => vouchers?.filter((v) => v.status === st).reduce((a, v) => a + v.value, 0) || 0;
  const count = (st) => vouchers?.filter((v) => v.status === st).length || 0;

  return (
    <div className="space-y-6" data-testid="admin-vouchers-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Cadeaux</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Bons cadeaux</h2>
        </div>
        {vouchers && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400" data-testid="vouchers-kpis">
            <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-amber-300">{count("pending")} à activer</span>
            <span className="rounded-full border border-white/10 px-3 py-1.5">Actifs <span className="font-outfit text-base font-semibold tabular-nums text-glow">{eur(sum("paid"))}</span></span>
            <span className="rounded-full border border-white/10 px-3 py-1.5">Utilisés <span className="font-outfit text-base font-semibold tabular-nums text-white">{count("redeemed")}</span></span>
          </div>
        )}
      </div>
      <p className="text-xs text-slate-500">
        Une demande arrive par email à chaque commande. Une fois le paiement reçu, cliquez « Activer » : le bon devient valable 12 mois et l'acheteur reçoit son code. Le bon se marque « Utilisé » automatiquement lors de la réservation.
      </p>

      {vouchers && vouchers.length === 0 && (
        <div className="rounded-2xl border border-dashed border-white/15 bg-panel/40 p-10 text-center text-sm text-slate-500" data-testid="vouchers-empty">Aucun bon cadeau pour le moment.</div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {vouchers?.map((v, i) => {
          const st = STATUS[v.status] || STATUS.pending;
          return (
            <motion.article
              key={v.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.04 }}
              data-testid={`voucher-${v.id}`}
              className={`rounded-2xl border p-5 backdrop-blur-xl ${v.status === "paid" ? "border-gold/30 bg-gold/5" : "border-white/10 bg-panel/70"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <button data-testid={`voucher-copy-${v.id}`} onClick={() => copy(v.code)} title="Copier le code" className="inline-flex items-center gap-2 rounded-xl border border-dashed border-gold/50 bg-abyss px-3 py-2 font-mono text-sm tracking-[0.2em] text-white transition-colors hover:border-gold">
                  <Gift size={14} className="text-gold" /> {v.code} <Copy size={12} className="text-slate-500" />
                </button>
                <span data-testid={`voucher-status-${v.id}`} className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] ${st.cls}`}>{st.label}</span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                <p className="text-slate-500">Acheteur <span className="block text-sm text-white">{v.buyer_name}</span><span className="text-[11px] text-slate-500">{v.buyer_email}</span></p>
                <p className="text-slate-500">Pour <span className="block text-sm text-white">{v.recipient_name}</span></p>
                <p className="text-slate-500">Expérience <span className="block text-sm text-white">{EXP_LABELS[v.experience]} · {v.participants} pers.</span></p>
                <p className="text-slate-500">Valeur <span className="block font-outfit text-lg font-semibold tabular-nums text-gold">{eur(v.value)}</span></p>
                <p className="text-slate-500">Créé le <span className="block text-sm text-slate-300">{fmt(v.created_at)}</span></p>
                <p className="text-slate-500">{v.status === "redeemed" ? "Utilisé le" : "Valable jusqu'au"} <span className="block text-sm text-slate-300">{fmt(v.status === "redeemed" ? v.redeemed_at : v.expires_at)}</span></p>
              </div>
              {v.message && <p className="mt-3 font-cormorant text-base italic text-slate-300">« {v.message} »</p>}
              <div className="mt-4 flex flex-wrap gap-2">
                <button data-testid={`voucher-pdf-${v.id}`} onClick={() => downloadPdf(v)} className="inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3 py-1.5 text-xs font-semibold text-gold hover:bg-gold/20">
                  <FileDown size={13} /> PDF
                </button>
                {v.status === "pending" && (
                  <button data-testid={`voucher-activate-${v.id}`} disabled={busy === v.id} onClick={() => setStatus(v, "paid", "Bon activé — code envoyé à l'acheteur")} className="inline-flex items-center gap-1.5 rounded-full border border-glow/50 bg-glow/10 px-3 py-1.5 text-xs font-semibold text-glow hover:bg-glow/20 disabled:opacity-40">
                    <CheckCircle2 size={13} /> Activer (paiement reçu)
                  </button>
                )}
                {(v.status === "paid" || v.status === "redeemed") && (
                  <button data-testid={`voucher-resend-${v.id}`} disabled={busy === v.id} onClick={() => resend(v)} className="inline-flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:border-glow/50 hover:text-glow disabled:opacity-40">
                    <Mail size={13} /> Renvoyer le code{v.email_sent === false ? " (échec précédent)" : ""}
                  </button>
                )}
                {v.status === "redeemed" && (
                  <button data-testid={`voucher-release-${v.id}`} disabled={busy === v.id} onClick={() => setStatus(v, "paid", "Bon remis en circulation")} className="inline-flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:border-gold/50 hover:text-gold disabled:opacity-40">
                    <RotateCcw size={13} /> Remettre en circulation
                  </button>
                )}
                {v.status !== "cancelled" && v.status !== "redeemed" && (
                  <button data-testid={`voucher-cancel-${v.id}`} disabled={busy === v.id} onClick={() => setStatus(v, "cancelled", "Bon annulé")} className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-500 hover:border-red-400/50 hover:text-red-300 disabled:opacity-40">
                    <Ban size={13} /> Annuler
                  </button>
                )}
                {v.status === "cancelled" && (
                  <button data-testid={`voucher-reactivate-${v.id}`} disabled={busy === v.id} onClick={() => setStatus(v, "paid", "Bon réactivé")} className="inline-flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:text-glow disabled:opacity-40">
                    <RotateCcw size={13} /> Réactiver
                  </button>
                )}
              </div>
            </motion.article>
          );
        })}
      </div>
    </div>
  );
};

export default AdminVouchers;
