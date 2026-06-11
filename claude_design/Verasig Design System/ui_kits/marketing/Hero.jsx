/* Verasig Marketing — Hero */
function HeroTrace() {
  return (
    <svg className="mk-hero__trace" viewBox="0 0 520 120" fill="none" preserveAspectRatio="none">
      <path d="M0 78 L60 78 L92 78 L120 96 L150 34 L182 64 L212 64 L260 64 L300 50 L340 70 L380 26 L430 56 L470 44 L520 44"
        stroke="var(--signal-500)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="520" cy="44" r="4" fill="var(--signal-500)" />
    </svg>
  );
}

function Hero() {
  const { Button, StatusPill, ConfidenceBar } = window.VerasigDesignSystem_fd565b;
  const Arrow = () => <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;

  return (
    <section className="mk-hero v-lattice">
      <div className="mk-hero__glow" />
      <div className="mk-hero__inner">
        <div className="mk-hero__copy">
          <span className="v-eyebrow mk-hero__eyebrow"><span className="mk-dot" />Signal verification infrastructure</span>
          <h1 className="mk-hero__title">Trust<br />every signal.</h1>
          <p className="mk-hero__sub">Verasig sits between your providers and the systems that act on them — cross-checking every signal across independent sources before it ever reaches production.</p>
          <div className="mk-hero__cta">
            <Button variant="primary" size="lg" iconRight={<Arrow />}>Talk to us</Button>
            <Button variant="secondary" size="lg">Explore products</Button>
          </div>
          <div className="mk-hero__meta">
            <span><b>4.1B+</b> signals verified</span>
            <span className="mk-sep" />
            <span><b>120+</b> providers</span>
            <span className="mk-sep" />
            <span><b>99.98%</b> uptime</span>
          </div>
        </div>

        <div className="mk-hero__panel">
          <div className="mk-panel">
            <div className="mk-panel__head">
              <span className="mk-mono">SIG-7F2A · BTC/USD</span>
              <StatusPill status="verified" />
            </div>
            <HeroTrace />
            <div className="mk-panel__rows">
              <div className="mk-panel__row"><span className="mk-mono-f">Sources</span><span className="mk-mono">12 / 12 agreed</span></div>
              <div className="mk-panel__row"><span className="mk-mono-f">Latency</span><span className="mk-mono">182&nbsp;ms</span></div>
              <ConfidenceBar value={99.4} threshold={80} label="Confidence" />
            </div>
          </div>
          <div className="mk-panel mk-panel--ghost">
            <div className="mk-panel__head">
              <span className="mk-mono">SIG-7F19 · ELECTION-2028</span>
              <StatusPill status="pending" pulse />
            </div>
            <div className="mk-panel__rows">
              <div className="mk-panel__row"><span className="mk-mono-f">Quorum</span><span className="mk-mono">9 / 14 · holding</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
window.Hero = Hero;
