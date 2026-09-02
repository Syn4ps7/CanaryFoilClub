const ITEMS = [
  "FLITEBOARD SERIES 6 — AUTHORIZED",
  "100% ELECTRIC HYDROFOIL",
  "BB TALKIN RADIO GUIDANCE",
  "MOBILE VIP BASE CAMP — COSTA ADEJE",
  "ZERO EMISSIONS · PURE SILENCE",
  "FLIGHT GUARANTEED ON DAY ONE",
];

const Row = () => (
  <div className="flex shrink-0 items-center">
    {ITEMS.map((item, i) => (
      <span key={i} className="flex items-center">
        <span className="px-8 font-cormorant italic text-xl sm:text-2xl text-slate-300 whitespace-nowrap">
          {item}
        </span>
        <span className="h-2 w-2 rotate-45 border border-gold/70 shrink-0" />
      </span>
    ))}
  </div>
);

const Marquee = () => (
  <div data-testid="editorial-marquee" className="relative overflow-hidden border-y border-white/10 bg-deep/70 py-5">
    <div className="marquee-track flex w-max">
      <Row />
      <Row />
    </div>
  </div>
);

export default Marquee;
