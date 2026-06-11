/* Verasig Marketing — Why + CTA + Footer */
const MK_WHY_ICONS = {
  pulse: <path d="M3 12h4l2 6 4-14 3 10 2-4h3" />,
  sources: <><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="12" cy="18" r="2.5" /><path d="M7.7 7.7 11 15M16.3 7.7 13 15" /></>,
  tune: <><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3" /><path d="M1 14h6M9 8h6M17 16h6" /></>,
  shield: <><path d="M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6l-8-3Z" /><path d="m9 12 2 2 4-4" /></>,
};
function Why() {
  const { why } = window.VRS_SITE;
  return (
    <section className="mk-sec" id="why">
      <div className="mk-sec__head">
        <span className="v-eyebrow"><span className="mk-dot" />Why Verasig</span>
        <h2 className="mk-sec__title">The trust layer<br />signals were missing.</h2>
      </div>
      <div className="mk-why">
        {why.map((w) => (
          <div className="mk-why__item" key={w.title}>
            <span className="mk-why__ic">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{MK_WHY_ICONS[w.icon]}</svg>
            </span>
            <div className="mk-why__t">{w.title}</div>
            <p className="mk-why__b">{w.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
window.Why = Why;

function CTA() {
  const { Button } = window.VerasigDesignSystem_fd565b;
  const Arrow = () => <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
  const Book = () => <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></svg>;
  return (
    <section className="mk-cta v-lattice">
      <div className="mk-cta__glow" />
      <div className="mk-cta__inner">
        <h2 className="mk-cta__title">Tell us what you're verifying.</h2>
        <p className="mk-cta__sub">From market data to device telemetry to real-world outcomes — bring us the signal, we'll bring it to production.</p>
        <div className="mk-cta__btns">
          <Button variant="primary" size="lg" iconRight={<Arrow />}>Talk to us</Button>
          <Button variant="secondary" size="lg" iconLeft={<Book />}>Read the docs</Button>
        </div>
      </div>
    </section>
  );
}
window.CTA = CTA;

function Footer() {
  const cols = [
    { h: 'Products', links: ['Verify', 'Quorum', 'Channels', 'Provenance'] },
    { h: 'Developers', links: ['Docs', 'API reference', 'Status', 'Changelog'] },
    { h: 'Company', links: ['About', 'Customers', 'Careers', 'Contact'] },
  ];
  return (
    <footer className="mk-foot">
      <div className="mk-foot__inner">
        <div className="mk-foot__brand">
          <a className="mk-nav__brand" href="#">
            <svg width="24" height="24" viewBox="0 0 40 40" fill="none" style={{ color: 'var(--signal-500)' }}>
              <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="30" cy="18" r="3.4" fill="currentColor" />
            </svg>
            <span>Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></span>
          </a>
          <p className="mk-foot__tag">The trust layer for signals.</p>
        </div>
        <div className="mk-foot__cols">
          {cols.map((c) => (
            <div className="mk-foot__col" key={c.h}>
              <div className="mk-foot__h">{c.h}</div>
              {c.links.map((l) => <a key={l} href="#">{l}</a>)}
            </div>
          ))}
        </div>
      </div>
      <div className="mk-foot__bar">
        <span>© 2026 Verasig, Inc.</span>
        <span className="mk-foot__legal"><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Security</a></span>
      </div>
    </footer>
  );
}
window.Footer = Footer;
