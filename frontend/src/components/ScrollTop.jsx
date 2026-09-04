import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp } from "lucide-react";

const ScrollTop = () => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = ({ scroll }) => setShow(scroll > window.innerHeight * 0.8);
    const lenis = window.__lenis;
    if (lenis) {
      lenis.on("scroll", onScroll);
      return () => lenis.off("scroll", onScroll);
    }
    const fallback = () => setShow(window.scrollY > window.innerHeight * 0.8);
    window.addEventListener("scroll", fallback, { passive: true });
    return () => window.removeEventListener("scroll", fallback);
  }, []);

  const toTop = () => {
    if (window.__lenis) window.__lenis.scrollTo(0, { duration: 1.6 });
    else window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.button
          data-testid="scroll-to-top-button"
          initial={{ opacity: 0, y: 24, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.9 }}
          whileHover={{ y: -4 }}
          whileTap={{ scale: 0.92 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          onClick={toTop}
          aria-label="Remonter en haut"
          className="fixed bottom-6 right-6 sm:bottom-8 sm:right-8 z-[80] grid h-12 w-12 place-items-center rounded-full border border-glow/40 bg-panel/80 text-glow backdrop-blur-xl shadow-[0_0_24px_rgba(0,240,255,0.25)] transition-colors hover:bg-glow hover:text-abyss"
        >
          <ArrowUp size={18} />
        </motion.button>
      )}
    </AnimatePresence>
  );
};

export default ScrollTop;
