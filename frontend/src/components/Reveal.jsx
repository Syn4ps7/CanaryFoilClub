import { motion } from "framer-motion";

export const Reveal = ({ children, delay = 0, y = 36, className = "" }) => (
  <motion.div
    initial={{ opacity: 0, y }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-70px" }}
    transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
    className={className}
  >
    {children}
  </motion.div>
);

export const SectionCaption = ({ children }) => (
  <p className="font-mono text-xs sm:text-sm tracking-[0.25em] uppercase text-glow/90 mb-6">
    {children}
  </p>
);
