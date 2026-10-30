function AuthMark({ size = 26 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      style={{ color: 'var(--signal-500)' }}
    >
      <path
        d="M4 22 L11 22 L17 30 L24 9 L30 18"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="30" cy="18" r="3.4" fill="currentColor" />
    </svg>
  )
}

export function BrandPanel() {
  return (
    <aside className="auth-brand v-lattice">
      <div className="auth-brand__glow" />
      <div className="auth-brand__top">
        <a className="auth-brand__logo" href="/">
          <AuthMark size={26} />
          Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
        </a>
      </div>
      <div className="auth-brand__mid">
        <div>
          <div className="auth-brand__head">
            Verify the signal
            <br />
            before you trade it.
          </div>
          <p className="auth-brand__sub" style={{ marginTop: 16 }}>
            Label what a real call looks like, backtest it across full history, and
            route only verified signals to your exchange.
          </p>
        </div>
        <div className="auth-card">
          <div className="auth-card__bar">
            <span className="auth-card__dot" />
            <span className="auth-card__name">Delta Futures Signals</span>
            <span className="auth-card__tag">@deltafutures</span>
            <span className="auth-card__ex">Example</span>
          </div>
          <div className="auth-card__metrics">
            <div className="auth-metric">
              <span className="auth-metric__v is-good">86</span>
              <span className="auth-metric__l">Quality / 100</span>
            </div>
            <div className="auth-metric">
              <span className="auth-metric__v">64.2%</span>
              <span className="auth-metric__l">Win rate</span>
            </div>
            <div className="auth-metric">
              <span className="auth-metric__v">18,420</span>
              <span className="auth-metric__l">Msgs tested</span>
            </div>
          </div>
        </div>
      </div>
      <div className="auth-brand__foot">
        <span>Telegram source</span>
        <span className="dot" />
        <span>Trade-only keys</span>
        <span className="dot" />
        <span>Backtest before live</span>
      </div>
    </aside>
  )
}
