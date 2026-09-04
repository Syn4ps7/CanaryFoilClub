import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Eye, EyeOff, Star, Trash2, Sparkles } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";
import { Stars } from "@/components/Testimonials";
import { EXP_LABELS } from "@/components/admin/BookingsTable";

const AdminReviews = ({ onLogout }) => {
  const [reviews, setReviews] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await adminApi.get("/admin/reviews");
      setReviews(data);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const patch = async (id, body, msg) => {
    setBusy(id);
    try {
      await adminApi.patch(`/admin/reviews/${id}`, body);
      toast.success(msg);
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Supprimer définitivement cet avis ?")) return;
    setBusy(id);
    try {
      await adminApi.delete(`/admin/reviews/${id}`);
      toast.success("Avis supprimé");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const approved = reviews?.filter((r) => r.approved) || [];
  const avg = reviews?.length ? (reviews.reduce((a, r) => a + r.rating, 0) / reviews.length).toFixed(1) : "—";
  const pending = reviews?.filter((r) => !r.approved).length || 0;

  return (
    <div className="space-y-6" data-testid="admin-reviews-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Réputation</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Avis clients</h2>
        </div>
        {reviews && (
        <div className="flex items-center gap-3 text-xs text-slate-400" data-testid="reviews-kpis">
          <span className="rounded-full border border-white/10 px-3 py-1.5">Note moyenne <span className="font-outfit text-base font-semibold tabular-nums text-gold">{avg}</span>/5</span>
          <span className="rounded-full border border-white/10 px-3 py-1.5"><span className="font-outfit text-base font-semibold tabular-nums text-white">{approved.length}</span> publié{approved.length > 1 ? "s" : ""}</span>
          {pending > 0 && <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1.5 text-amber-300">{pending} à modérer</span>}
        </div>
        )}
      </div>

      <p className="text-xs text-slate-500">
        La demande d'avis est envoyée automatiquement le lendemain de chaque session (à partir de 9h) aux clients confirmés ou réalisés. Seuls les avis approuvés ici apparaissent sur le site.
      </p>

      {reviews && reviews.length === 0 && (
        <div className="rounded-2xl border border-dashed border-white/15 bg-panel/40 p-10 text-center text-sm text-slate-500" data-testid="reviews-empty">
          Aucun avis pour le moment.
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {reviews?.map((r, i) => (
          <motion.article
            key={r.id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.04 }}
            data-testid={`admin-review-${r.id}`}
            className={`rounded-2xl border p-5 backdrop-blur-xl ${r.approved ? (r.featured ? "border-gold/40 bg-gold/5" : "border-glow/30 bg-panel/70") : "border-amber-400/30 bg-panel/70"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Stars value={r.rating} />
                  <span className="font-outfit text-sm font-semibold tabular-nums text-white">{r.rating}/5</span>
                </div>
                <p className="mt-1 text-sm font-medium text-white">{r.name} <span className="text-slate-500">· {EXP_LABELS[r.experience] || r.experience} · {new Date(r.date).toLocaleDateString("fr-FR")}</span></p>
              </div>
              <span data-testid={`review-status-${r.id}`} className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] ${r.approved ? "border-glow/40 text-glow" : "border-amber-400/40 text-amber-300"}`}>
                {r.approved ? "Publié" : "À modérer"}
              </span>
            </div>
            <p className="mt-3 font-cormorant text-lg italic leading-relaxed text-slate-200">« {r.comment} »</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                data-testid={`review-toggle-approve-${r.id}`}
                disabled={busy === r.id}
                onClick={() => patch(r.id, { approved: !r.approved }, r.approved ? "Avis masqué du site" : "Avis publié sur le site")}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${r.approved ? "border-white/15 text-slate-300 hover:border-white/40" : "border-glow/50 bg-glow/10 text-glow hover:bg-glow/20"}`}
              >
                {r.approved ? <EyeOff size={13} /> : <Eye size={13} />} {r.approved ? "Masquer" : "Publier"}
              </button>
              <button
                data-testid={`review-toggle-feature-${r.id}`}
                disabled={busy === r.id}
                onClick={() => patch(r.id, { featured: !r.featured }, r.featured ? "Avis retiré des favoris" : "Avis mis en avant")}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${r.featured ? "border-gold/50 bg-gold/10 text-gold" : "border-white/15 text-slate-300 hover:border-gold/40"}`}
              >
                <Sparkles size={13} /> {r.featured ? "En avant" : "Mettre en avant"}
              </button>
              <button data-testid={`review-delete-${r.id}`} disabled={busy === r.id} onClick={() => remove(r.id)} className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-red-400/50 hover:text-red-300">
                <Trash2 size={13} />
              </button>
            </div>
          </motion.article>
        ))}
      </div>
      <p className="text-[11px] text-slate-600 flex items-center gap-1"><Star size={11} /> Les avis « mis en avant » apparaissent en premier sur le site, avec un cadre doré.</p>
    </div>
  );
};

export default AdminReviews;
