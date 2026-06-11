/* Verasig Marketing — page composition */
function Site() {
  const { Nav, Hero, Products, Stats, Marquee, Why, CTA, Footer } = window;
  return (
    <div className="mk-page">
      <Nav />
      <Hero />
      <Marquee />
      <Products />
      <Stats />
      <Why />
      <CTA />
      <Footer />
    </div>
  );
}
window.Site = Site;
