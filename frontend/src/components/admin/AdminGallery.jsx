import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Upload, Trash2, ArrowUp, ArrowDown, Play, Check, Images } from "lucide-react";
import { adminApi, formatApiError } from "@/lib/adminApi";
import { mediaUrl } from "@/components/Gallery";

const ACCEPT = "image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime";

const CaptionField = ({ item, onSave }) => {
  const [v, setV] = useState(item.caption || "");
  useEffect(() => setV(item.caption || ""), [item.caption]);
  const dirty = v !== (item.caption || "");
  return (
    <div className="flex gap-2">
      <input
        data-testid={`gallery-caption-${item.id}`}
        value={v}
        maxLength={160}
        onChange={(e) => setV(e.target.value)}
        placeholder="Légende (facultatif)"
        className="w-full rounded-lg border border-white/15 bg-deep px-3 py-1.5 text-xs text-white placeholder:text-slate-500 outline-none focus:border-glow/70"
      />
      {dirty && (
        <button data-testid={`gallery-caption-save-${item.id}`} onClick={() => onSave(v)} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-glow/50 bg-glow/10 text-glow"><Check size={13} /></button>
      )}
    </div>
  );
};

const AdminGallery = ({ onLogout }) => {
  const [items, setItems] = useState(null);
  const [uploads, setUploads] = useState([]);
  const inputRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data } = await adminApi.get("/admin/gallery");
      setItems(data);
    } catch (err) {
      if (err?.response?.status === 401) onLogout();
      else toast.error(formatApiError(err));
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const uploadFiles = async (files) => {
    for (const file of Array.from(files)) {
      const key = `${file.name}-${Date.now()}`;
      setUploads((u) => [...u, { key, name: file.name, pct: 0 }]);
      const fd = new FormData();
      fd.append("file", file);
      try {
        await adminApi.post("/admin/gallery", fd, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 300000,
          onUploadProgress: (e) => setUploads((u) => u.map((x) => (x.key === key ? { ...x, pct: Math.round((e.loaded / (e.total || file.size)) * 100) } : x))),
        });
        toast.success(`${file.name} ajouté à la galerie`);
      } catch (err) {
        toast.error(`${file.name} : ${formatApiError(err)}`);
      } finally {
        setUploads((u) => u.filter((x) => x.key !== key));
      }
    }
    await load();
  };

  const patch = async (id, body) => {
    try {
      await adminApi.patch(`/admin/gallery/${id}`, body);
      toast.success("Légende enregistrée");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const move = async (index, dir) => {
    const next = [...items];
    const j = index + dir;
    if (j < 0 || j >= next.length) return;
    [next[index], next[j]] = [next[j], next[index]];
    setItems(next);
    try {
      await adminApi.post("/admin/gallery/reorder", { ids: next.map((i) => i.id) });
    } catch (err) {
      toast.error(formatApiError(err));
      load();
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Retirer ce média de la galerie ?")) return;
    try {
      await adminApi.delete(`/admin/gallery/${id}`);
      toast.success("Média retiré");
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-gallery-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Contenu</p>
          <h2 className="mt-1 font-syne text-2xl sm:text-3xl font-bold tracking-tight">Galerie photos & vidéos</h2>
        </div>
        <button data-testid="gallery-upload-button" onClick={() => inputRef.current?.click()} className="inline-flex items-center gap-2 rounded-full bg-glow px-5 py-2.5 font-syne text-xs font-bold text-abyss btn-glow">
          <Upload size={14} /> Ajouter des fichiers
        </button>
        <input ref={inputRef} data-testid="gallery-file-input" type="file" accept={ACCEPT} multiple className="hidden" onChange={(e) => { if (e.target.files?.length) uploadFiles(e.target.files); e.target.value = ""; }} />
      </div>

      <div
        data-testid="gallery-dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files); }}
        className="rounded-2xl border border-dashed border-white/15 bg-panel/40 px-6 py-8 text-center"
      >
        <Images size={22} className="mx-auto text-glow" />
        <p className="mt-2 text-sm text-slate-300">Glissez vos photos et vidéos ici</p>
        <p className="mt-1 text-xs text-slate-500">JPG, PNG, WebP, GIF, MP4, WebM, MOV · 60 Mo max par fichier · l'ordre ci-dessous est celui du site</p>
        {uploads.map((u) => (
          <div key={u.key} className="mx-auto mt-4 max-w-md text-left" data-testid="gallery-upload-progress">
            <p className="flex justify-between text-[11px] text-slate-400"><span className="truncate">{u.name}</span><span className="font-outfit tabular-nums">{u.pct} %</span></p>
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/5"><div className="h-full bg-glow transition-[width]" style={{ width: `${u.pct}%` }} /></div>
          </div>
        ))}
      </div>

      {items && items.length === 0 && <p className="text-center text-sm text-slate-500" data-testid="gallery-empty">Aucun média — la section Galerie est masquée sur le site tant qu'elle est vide.</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items?.map((item, i) => (
          <motion.div key={item.id} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} data-testid={`admin-gallery-item-${item.id}`} className="overflow-hidden rounded-2xl border border-white/10 bg-panel/70">
            <div className="relative aspect-[4/3] bg-abyss">
              {item.kind === "video" ? (
                <video src={mediaUrl(item.id)} muted loop playsInline preload="metadata" className="h-full w-full object-cover" onMouseEnter={(e) => e.target.play()} onMouseLeave={(e) => e.target.pause()} />
              ) : (
                <img src={mediaUrl(item.id)} alt="" className="h-full w-full object-cover" />
              )}
              <span className="absolute left-2 top-2 rounded-full border border-white/20 bg-abyss/70 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-white backdrop-blur">
                {item.kind === "video" ? <span className="inline-flex items-center gap-1"><Play size={9} className="fill-white" /> vidéo</span> : "photo"} · #{i + 1}
              </span>
            </div>
            <div className="space-y-2 p-3">
              <CaptionField item={item} onSave={(caption) => patch(item.id, { caption })} />
              <div className="flex items-center justify-between">
                <div className="flex gap-1">
                  <button data-testid={`gallery-move-up-${item.id}`} disabled={i === 0} onClick={() => move(i, -1)} className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-slate-300 hover:text-glow disabled:opacity-30"><ArrowUp size={13} /></button>
                  <button data-testid={`gallery-move-down-${item.id}`} disabled={i === items.length - 1} onClick={() => move(i, 1)} className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-slate-300 hover:text-glow disabled:opacity-30"><ArrowDown size={13} /></button>
                </div>
                <span className="text-[10px] text-slate-500">{(item.size / 1024 / 1024).toFixed(1)} Mo{item.width ? ` · ${item.width}×${item.height}` : ""}</span>
                <button data-testid={`gallery-delete-${item.id}`} onClick={() => remove(item.id)} className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-slate-500 hover:border-red-400/50 hover:text-red-300"><Trash2 size={13} /></button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default AdminGallery;
