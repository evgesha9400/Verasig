/* Verasig Marketing — Products + Stats + Marquee */
function Products() {
  const { products } = window.VRS_SITE;
  const Arrow = () => <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
  return (
    <section className="mk-sec" id="products">
      <div className="mk-sec__head">
        <span className="v-eyebrow"><span className="mk-dot" />Products</span>
        <h2 className="mk-sec__title">One integration.<br />Every signal verified.</h2>
        <p className="mk-sec__lead">Compose the building blocks of trust — from ingestion to a signed, auditable decision.</p>
      </div>
      <div className="mk-products">
        {products.map((p) => (
          <a className="mk-prod" key={p.id} href="#">
            <div className="mk-prod__top">
              <span className="mk-prod__sw" style={{ background: p.tint }} />
              <span className="mk-prod__name">{p.name}</span>
            </div>
            <div className="mk-prod__tag">{p.tagline}</div>
            <p className="mk-prod__body">{p.body}</p>
            <div className="mk-prod__foot">
              <div className="mk-prod__stat"><span className="mk-prod__statv" style={{ color: p.tint }}>{p.stat}</span><span className="mk-prod__statl">{p.statLabel}</span></div>
              <span className="mk-prod__more">Learn more <Arrow /></span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
window.Products = Products;

function Stats() {
  const { stats } = window.VRS_SITE;
  return (
    <section className="mk-stats">
      <div className="mk-stats__inner">
        {stats.map((s) => (
          <div className="mk-stat" key={s.label}>
            <div className="mk-stat__v">{s.value}</div>
            <div className="mk-stat__l">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
window.Stats = Stats;

function Marquee() {
  const { providers } = window.VRS_SITE;
  const loop = [...providers, ...providers];
  return (
    <section className="mk-marquee" id="providers">
      <div className="mk-marquee__label v-eyebrow">Verifying signals from</div>
      <div className="mk-marquee__viewport">
        <div className="mk-marquee__track">
          {loop.map((p, i) => <span className="mk-chip" key={i}>{p}</span>)}
        </div>
      </div>
    </section>
  );
}
window.Marquee = Marquee;
