import { useEffect, useState } from "react";
import Lenis from "lenis";
import { AnimatePresence, motion } from "framer-motion";
import { LanguageProvider } from "@/i18n/LanguageContext";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Marquee from "@/components/Marquee";
import Pillars from "@/components/Pillars";
import Experiences from "@/components/Experiences";
import Corporate from "@/components/Corporate";
import Reseller from "@/components/Reseller";
import Testimonials from "@/components/Testimonials";
import GiftSection from "@/components/GiftSection";
import Gallery from "@/components/Gallery";
import GiftModal from "@/components/GiftModal";
import BookingModal from "@/components/BookingModal";
import Footer from "@/components/Footer";
import ScrollTop from "@/components/ScrollTop";

const Intro = () => (
  <motion.div
    exit={{ y: "-100%" }}
    transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
    className="pointer-events-none fixed inset-0 z-[100] grid place-items-center bg-abyss"
  >
    <div className="overflow-hidden">
      <motion.p
        initial={{ y: "110%" }}
        animate={{ y: 0 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        className="font-syne text-2xl sm:text-4xl font-extrabold tracking-[0.25em]"
      >
        CANARY <span className="text-glow">FOIL</span> CLUB
      </motion.p>
    </div>
    <motion.div
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      transition={{ duration: 1.1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="absolute bottom-0 left-0 h-[2px] w-full origin-left bg-glow"
    />
  </motion.div>
);

export default function Landing() {
  const [intro, setIntro] = useState(true);
  const [booking, setBooking] = useState({ open: false, preset: null, code: null });

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("code");
    if (code) {
      const timer = setTimeout(() => setBooking({ open: true, preset: null, code }), 2100);
      return () => clearTimeout(timer);
    }
  }, []);
  const [gift, setGift] = useState(false);

  useEffect(() => {
    const lenis = new Lenis({ duration: 1.25, smoothWheel: true });
    window.__lenis = lenis;
    let raf;
    const loop = (time) => {
      lenis.raf(time);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
      window.__lenis = null;
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setIntro(false), 1900);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const lenis = window.__lenis;
    const locked = booking.open || gift;
    document.documentElement.style.overflow = locked ? "hidden" : "";
    document.body.style.overflow = locked ? "hidden" : "";
    if (!lenis) return;
    if (locked) lenis.stop();
    else lenis.start();
  }, [booking.open, gift]);

  const openBooking = (preset = null) => setBooking({ open: true, preset });

  return (
    <LanguageProvider>
      <div className="App noise-overlay">
        <AnimatePresence>{intro && <Intro />}</AnimatePresence>
        <Navbar onBook={openBooking} />
        <main>
          <Hero onBook={openBooking} />
          <Marquee />
          <Pillars />
          <Experiences onBook={openBooking} />
          <Corporate onBook={openBooking} />
          <Gallery />
          <Testimonials />
          <GiftSection onGift={() => setGift(true)} />
          <Reseller onBook={openBooking} />
        </main>
        <Footer />
        <GiftModal open={gift} onClose={() => setGift(false)} />
        <ScrollTop />
        <BookingModal
          open={booking.open}
          preset={booking.preset}
          presetCode={booking.code}
          onClose={() => setBooking({ open: false, preset: null, code: null })}
        />
      </div>
    </LanguageProvider>
  );
}
