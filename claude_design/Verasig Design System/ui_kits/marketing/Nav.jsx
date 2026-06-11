/* Verasig Marketing — Nav */
function Nav() {
  const { Button } = window.VerasigDesignSystem_fd565b;
  return (
    <header className="mk-nav">
      <div className="mk-nav__inner">
        <a className="mk-nav__brand" href="#">
          <svg width="26" height="26" viewBox="0 0 40 40" fill="none" style={{ color: 'var(--signal-500)' }}>
            <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="30" cy="18" r="3.4" fill="currentColor" />
          </svg>
          <span>Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></span>
        </a>
        <nav className="mk-nav__links">
          <a href="#products">Products</a>
          <a href="#why">Why Verasig</a>
          <a href="#providers">Providers</a>
          <a href="#docs">Docs</a>
        </nav>
        <div className="mk-nav__actions">
          <a className="mk-nav__signin" href="#">Sign in</a>
          <Button variant="primary" size="sm">Talk to us</Button>
        </div>
      </div>
    </header>
  );
}
window.Nav = Nav;
