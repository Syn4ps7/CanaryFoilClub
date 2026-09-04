import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Play, ChevronLeft, ChevronRight } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { Reveal, SectionCaption } from "./Reveal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const mediaUrl = (id) => `${API}/gallery/${id}/file`;

const spanFor = (item, i) => {
  const ratio = item.width && item.height ? item.width / item.height : 1.4;
  if (item.kind === "video" || i % 5 === 0) return "md:col-span-2 md:row-span-2";
  if (ratio < 0.9) return "md:row-span-2";
  return "";
};

const Lightbox = ({ items, index, onClose, onMove }) => {
  const item = items[index];
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onMove(1);
      if (e.key === "ArrowLeft") onMove(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onMove]);
  return (
    <motion.div
      data-testid="gallery-lightbox"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[96] flex items-center justify-center bg-abyss/95 backdrop-blur-md p-4 sm:p-10"
      onClick={onClose}
    >
      <button data-testid="gallery-lightbox-close" onClick={onClose} aria-label="Close" className="absolute right-5 top-5 grid h-11 w-11 place-items-center rounded-full border border-white/15 text-white transition-colors hover:border-glow hover:text-glow">
        <X size={20} />
      </button>
      {items.length > 1 && (
        <>
          <button data-testid="gallery-lightbox-prev" onClick={(e) => { e.stopPropagation(); onMove(-1); }} className="absolute left-4 top-1/2 -translate-y-1/2 grid h-11 w-11 place-items-center rounded-full border border-white/15 text-white hover:border-glow hover:text-glow"><ChevronLeft /></button>
          <button data-testid="gallery-lightbox-next" onClick={(e) => { e.stopPropagation(); onMove(1); }} className="absolute right-4 top-1/2 -translate-y-1/2 grid h-11 w-11 place-items-center rounded-full border border-white/15 text-white hover:border-glow hover:text-glow"><ChevronRight /></button>
        </>
      )}
      <motion.div key={item.id} initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.35 }} className="max-h-full max-w-6xl" onClick={(e) => e.stopPropagation()}>
        {item.kind === "video" ? (
          <video src={mediaUrl(item.id)} controls autoPlay playsInline className="max-h-[80vh] rounded-2xl" />
        ) : (
          <img src={mediaUrl(item.id)} alt={item.caption || "Canary Foil Club"} className="max-h-[80vh] rounded-2xl object-contain" />
        )}
        {item.caption && <p className="mt-4 text-center font-cormorant text-xl italic text-slate-200">{item.caption}</p>}
      </motion.div>
    </motion.div>
  );
};

const Gallery = () => {
  const { t } = useLanguage();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    fetch(`${API}/gallery`).then((r) => (r.ok ? r.json() : [])).then(setItems).catch(() => setItems([]));
  }, []);

  useEffect(() => {
    const lenis = window.__lenis;
    document.documentElement.style.overflow = open !== null ? "hidden" : "";
    if (lenis) open !== null ? lenis.stop() : lenis.start();
  }, [open]);

  if (!items.length) return null;
  const move = (d) => setOpen((i) => (i + d + items.length) % items.length);

  return (
    <section id="gallery" data-testid="gallery-section" className="relative py-28 sm:py-36 overflow-hidden">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionCaption>{t.gallery.caption}</SectionCaption>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h2 className="font-syne font-bold tracking-tight leading-tight text-2xl sm:text-3xl lg:text-4xl">{t.gallery.title}</h2>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">{items.length} · {t.gallery.subtitle}</p>
          </div>
        </Reveal>
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 auto-rows-[180px] md:auto-rows-[220px] gap-3 sm:gap-4">
          {items.map((item, i) => (
            <Reveal key={item.id} delay={0.05 * (i % 4)} className={spanFor(item, i)}>
              <motion.button
                data-testid={`gallery-item-${item.id}`}
                onClick={() => setOpen(i)}
                whileHover={{ scale: 0.985 }}
                className="group relative h-full w-full overflow-hidden rounded-2xl border border-white/10 bg-panel text-left"
              >
                {item.kind === "video" ? (
                  <video src={mediaUrl(item.id)} muted loop autoPlay playsInline preload="metadata" className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
                ) : (
                  <img src={mediaUrl(item.id)} alt={item.caption || "Canary Foil Club"} loading="lazy" className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-abyss/80 via-transparent to-transparent opacity-80 transition-opacity group-hover:opacity-100" />
                {item.kind === "video" && (
                  <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full border border-white/20 bg-abyss/60 px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.2em] text-white backdrop-blur">
                    <Play size={10} className="fill-white" /> {t.gallery.video}
                  </span>
                )}
                {item.caption && <p className="absolute bottom-3 left-4 right-4 truncate font-cormorant text-base italic text-white">{item.caption}</p>}
              </motion.button>
            </Reveal>
          ))}
        </div>
      </div>
      <AnimatePresence>{open !== null && <Lightbox items={items} index={open} onClose={() => setOpen(null)} onMove={move} />}</AnimatePresence>
    </section>
  );
};

export default Gallery;
