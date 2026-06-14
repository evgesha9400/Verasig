/* Verasig — login & registration pages. Prefilled for click-through:
   submitting (or pressing Enter) routes into the app at index.html. */
const { useState } = React;
const ADS = window.VerasigDesignSystem_fd565b;

function AuthMark({ size = 26 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      style={{ color: "var(--signal-500)" }}
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
  );
}

/* ---- branded showcase panel (left) ---- */
function BrandPanel() {
  return (
    <aside className="auth-brand v-lattice">
      <div className="auth-brand__glow" />
      <div className="auth-brand__top">
        <a className="auth-brand__logo" href="Marketing.html">
          <AuthMark size={26} />
          Verasig<span style={{ color: "var(--signal-500)" }}>.</span>
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
            Label what a real call looks like, backtest it across full history,
            and route only verified signals to your exchange.
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
  );
}

function AuthPage({ mode }) {
  const { Button, Input, Checkbox } = ADS;
  const isRegister = mode === "register";
  const enter = (e) => {
    if (e) e.preventDefault();
    window.location.href = "index.html";
  };

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="Marketing.html">
            <AuthMark size={24} />
            Verasig<span style={{ color: "var(--signal-500)" }}>.</span>
          </a>

          <div className="auth-eyebrow">
            {isRegister ? "Get started" : "Welcome back"}
          </div>
          <h1 className="auth-title">
            {isRegister ? "Create your account" : "Log in to Verasig"}
          </h1>
          <p className="auth-lede">
            {isRegister
              ? "Connect a source and verify your first channel in a couple of minutes."
              : "Pick up where your sources left off."}
          </p>

          <form className="auth-form" onSubmit={enter}>
            {isRegister && (
              <Input
                label="Full name"
                required
                defaultValue="Mara Voss"
                iconLeft={<Icon name="users" size={16} />}
                placeholder="e.g. Mara Voss"
              />
            )}

            <Input
              label="Email"
              type="email"
              required
              defaultValue="mara@northwave.io"
              iconLeft={<Icon name="users" size={16} />}
              placeholder="you@company.com"
            />

            <Input
              label="Password"
              type="password"
              required
              defaultValue="verasig-demo-2026"
              iconLeft={<Icon name="lock" size={16} />}
              placeholder="••••••••"
              hint={isRegister ? "At least 10 characters." : undefined}
            />

            {!isRegister && (
              <div className="auth-row">
                <Checkbox label="Remember me" defaultChecked />
                <a className="auth-forgot" href="#">
                  Forgot password?
                </a>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              iconRight={<Icon name="arrowRight" size={16} />}
              onClick={enter}
            >
              {isRegister ? "Create account" : "Log in"}
            </Button>
          </form>

          {isRegister && (
            <p className="auth-legal">
              By creating an account you agree to our <a href="#">Terms</a> and{" "}
              <a href="#">Privacy Policy</a>.
            </p>
          )}

          <div className="auth-switch">
            {isRegister ? (
              <>
                Already have an account? <a href="Login.html">Log in</a>
              </>
            ) : (
              <>
                New to Verasig? <a href="Register.html">Create an account</a>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

window.AuthPage = AuthPage;
