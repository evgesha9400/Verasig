import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { Button, Icon } from '@verasig/design-system'
import './marketing.css'

/* ---------- brand mark ---------- */
function Mark({ size = 26 }) {
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

/* ========================================================== NAV ===== */
function Nav({ loginPath, signupPath }) {
  return (
    <header className="mk-nav">
      <div className="mk-nav__inner">
        <a className="mk-nav__brand" href="#top">
          <Mark size={26} />
          <span>
            Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
          </span>
        </a>
        <nav className="mk-nav__links">
          <a href="#how">How it works</a>
          <a href="#integrations">Integrations</a>
          <a href="#principles">Principles</a>
        </nav>
        <div className="mk-nav__actions">
          <Link className="mk-nav__signin" to={loginPath}>
            Log in
          </Link>
          <Button as={Link} to={signupPath} variant="primary" size="sm">
            Sign up
          </Button>
        </div>
      </div>
    </header>
  )
}

/* ========================================================== HERO ===== */
function HeroTrace() {
  return (
    <svg
      className="mk-hero__trace"
      viewBox="0 0 520 120"
      fill="none"
      preserveAspectRatio="none"
    >
      <path
        d="M0 78 L60 78 L92 78 L120 96 L150 34 L182 64 L212 64 L260 64 L300 50 L340 70 L380 26 L430 56 L470 44 L520 44"
        stroke="var(--signal-500)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="520" cy="44" r="4" fill="var(--signal-500)" />
    </svg>
  )
}

function Hero({ loginPath, signupPath }) {
  const pipe = ['Backfill', 'Mine', 'Verify', 'Backtest']
  return (
    <section className="mk-hero v-lattice" id="top">
      <div className="mk-hero__glow" />
      <div className="mk-hero__inner">
        <div className="mk-hero__copy">
          <span className="v-eyebrow mk-hero__eyebrow">
            <span className="mk-dot" />
            Signal verification for traders
          </span>
          <h1 className="mk-hero__title">
            Verify the signal
            <br />
            before you trade it.
          </h1>
          <p className="mk-hero__sub">
            Verasig connects to your Telegram signal channels, learns what a real call
            looks like from the channel’s own history, backtests it across that history,
            and routes only verified signals to your exchange.
          </p>
          <div className="mk-hero__cta">
            <Button
              as={Link}
              to={signupPath}
              variant="primary"
              size="lg"
              iconRight={<Icon name="arrowRight" size={16} />}
            >
              Sign up
            </Button>
            <Button as={Link} to={loginPath} variant="secondary" size="lg">
              Log in
            </Button>
          </div>
          <div className="mk-caps">
            <span className="mk-cap">
              <Icon name="telegram" size={14} fill />
              Telegram today · Discord soon
            </span>
            <span className="mk-cap">
              <Icon name="chart" size={14} />
              Backtest before live
            </span>
            <span className="mk-cap">
              <Icon name="lock" size={14} />
              Trade-only API keys
            </span>
          </div>
        </div>

        <div className="mk-preview">
          <div className="mk-pv-card">
            <div className="mk-pv-card__bar">
              <span className="mk-pv-card__dot" />
              <span className="mk-pv-card__name">Delta Futures Signals</span>
              <span className="mk-pv-card__tag">@deltafutures</span>
              <span className="mk-pv-card__ex">Example</span>
            </div>
            <div className="mk-pv-body">
              <HeroTrace />
              <div className="mk-pv-metrics">
                <div className="mk-pv-metric">
                  <span className="mk-pv-metric__v is-good">86</span>
                  <span className="mk-pv-metric__l">Quality / 100</span>
                </div>
                <div className="mk-pv-metric">
                  <span className="mk-pv-metric__v">64.2%</span>
                  <span className="mk-pv-metric__l">Win rate</span>
                </div>
                <div className="mk-pv-metric">
                  <span className="mk-pv-metric__v">18,420</span>
                  <span className="mk-pv-metric__l">Msgs tested</span>
                </div>
              </div>
            </div>
          </div>
          <div className="mk-pv-card">
            <div className="mk-pv-card__bar">
              <span
                className="mk-pv-card__name"
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-3xs)',
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  color: 'var(--text-faint)',
                  fontWeight: 400
                }}
              >
                Verification pipeline
              </span>
            </div>
            <div className="mk-pv-body" style={{ paddingTop: 20, paddingBottom: 20 }}>
              <div className="mk-pv-pipe">
                {pipe.map((s, i) => (
                  <Fragment key={s}>
                    {i > 0 && <span className="mk-pv-pipe__line" />}
                    <div className="mk-pv-pipe__step">
                      <span className="mk-pv-pipe__dot">
                        <Icon name="check" size={11} />
                      </span>
                      <span className="mk-pv-pipe__lbl">{s}</span>
                    </div>
                  </Fragment>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ==================================================== HOW IT WORKS ===== */
const FLOW = [
  {
    n: '01',
    ic: 'sources',
    t: 'Connect',
    b: 'Link a Telegram channel or group you belong to over MTProto. Read-only — Verasig never posts.'
  },
  {
    n: '02',
    ic: 'download',
    t: 'Backfill',
    b: 'Pull the full message history so verification runs on everything the channel has ever called.'
  },
  {
    n: '03',
    ic: 'sparkles',
    t: 'Mine',
    b: 'Verasig auto-detects the channel’s signal templates from its own history — no labeling, no configuration.'
  },
  {
    n: '04',
    ic: 'shield',
    t: 'Verify',
    b: 'Review the detected signal families and confirm the ones that match. Only what you accept moves on.'
  },
  {
    n: '05',
    ic: 'exchanges',
    t: 'Route',
    b: 'Send verified signals to a connected exchange — or just watch them stream, your call.'
  },
  {
    n: '06',
    ic: 'settings',
    t: 'Risk',
    b: 'Set position sizing and stops so a verified signal becomes an order you actually want.'
  },
  {
    n: '07',
    ic: 'chart',
    t: 'Backtest',
    b: 'Simulate the source over its history for a quality score and win rate before going live.'
  }
]
function HowItWorks() {
  return (
    <section className="mk-sec" id="how">
      <div className="mk-sec__head">
        <span className="v-eyebrow">
          <span className="mk-dot" />
          How it works
        </span>
        <h2 className="mk-sec__title">
          From a noisy channel
          <br />
          to a verified source.
        </h2>
        <p className="mk-sec__lead">
          Every source moves through the same pipeline. Nothing reaches your exchange
          until it has been mined, verified, and backtested.
        </p>
      </div>
      <div className="mk-flow">
        {FLOW.map((s) => (
          <div className="mk-flow__step" key={s.n}>
            <span className="mk-flow__ic">
              <Icon name={s.ic} size={20} />
            </span>
            <span className="mk-flow__n">{s.n}</span>
            <div className="mk-flow__t">{s.t}</div>
            <p className="mk-flow__b">{s.b}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ==================================================== INTEGRATIONS ===== */
function IntRow({ logoBg, logoColor, icon, name, kind, live }) {
  return (
    <div className={`mk-int ${live ? '' : 'is-soon'}`}>
      <span className="mk-int__logo" style={{ background: logoBg, color: logoColor }}>
        <Icon name={icon} size={24} fill />
      </span>
      <div className="mk-int__main">
        <div className="mk-int__name">{name}</div>
        <div className="mk-int__kind">{kind}</div>
      </div>
      <span className={`mk-int__state ${live ? 'is-live' : 'is-soon'}`}>
        {live ? 'Live' : 'Soon'}
      </span>
    </div>
  )
}
function Integrations() {
  return (
    <section className="mk-sec" id="integrations" style={{ paddingTop: 0 }}>
      <div className="mk-sec__head">
        <span className="v-eyebrow">
          <span className="mk-dot" />
          Integrations
        </span>
        <h2 className="mk-sec__title">
          Where signals come
          <br />
          from, and where they go.
        </h2>
      </div>
      <div className="mk-int-cols">
        <div className="mk-int-col">
          <div className="mk-int-col__h">
            <span className="mk-int-col__t">Sources</span>
            <span className="mk-int-col__s">where signals come from</span>
          </div>
          <div className="mk-int-list">
            <IntRow
              icon="telegram"
              logoBg="color-mix(in srgb, #2AABEE 22%, transparent)"
              logoColor="#3CB4F0"
              name="Telegram"
              kind="Channels & groups · MTProto"
              live
            />
            <IntRow
              icon="discord"
              logoBg="color-mix(in srgb, #5865F2 22%, transparent)"
              logoColor="#7B85F7"
              name="Discord"
              kind="Servers & channels · bot gateway"
            />
          </div>
        </div>
        <div className="mk-int-col">
          <div className="mk-int-col__h">
            <span className="mk-int-col__t">Exchanges</span>
            <span className="mk-int-col__s">where verified signals route</span>
          </div>
          <div className="mk-int-list">
            <IntRow
              icon="bybit"
              logoBg="color-mix(in srgb, #F7A600 18%, transparent)"
              logoColor="#F7A600"
              name="Bybit"
              kind="Derivatives & spot · trade-only key"
              live
            />
            <IntRow
              icon="binance"
              logoBg="color-mix(in srgb, #F0B90B 18%, transparent)"
              logoColor="#F0B90B"
              name="Binance"
              kind="Derivatives & spot"
            />
          </div>
        </div>
      </div>
    </section>
  )
}

/* ==================================================== PRINCIPLES ===== */
const PRINCIPLES = [
  {
    ic: 'check',
    t: 'It learns the channel',
    b: 'Verasig auto-detects a channel’s signal templates from its own history — your feed’s real format, not a generic model.'
  },
  {
    ic: 'shield',
    t: 'Verified, then trusted',
    b: 'You confirm the detected signal families before anything routes — only the ones you accept reach your exchange.'
  },
  {
    ic: 'chart',
    t: 'Backtested before live',
    b: 'Each source is simulated over its full history for a quality score and win rate, so you decide with evidence — not vibes.'
  },
  {
    ic: 'lock',
    t: 'Trade-only keys',
    b: 'Exchanges connect with trade-only API keys. Verasig places orders; it can never withdraw your funds.'
  }
]
function Principles() {
  return (
    <section className="mk-sec" id="principles" style={{ paddingTop: 0 }}>
      <div className="mk-sec__head">
        <span className="v-eyebrow">
          <span className="mk-dot" />
          Principles
        </span>
        <h2 className="mk-sec__title">
          Built to earn
          <br />
          your trust.
        </h2>
      </div>
      <div className="mk-why">
        {PRINCIPLES.map((p) => (
          <div className="mk-why__item" key={p.t}>
            <span className="mk-why__ic">
              <Icon name={p.ic} size={22} />
            </span>
            <div className="mk-why__t">{p.t}</div>
            <p className="mk-why__b">{p.b}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ==================================================== CTA + FOOTER ===== */
function CTA({ loginPath, signupPath }) {
  return (
    <section className="mk-cta v-lattice">
      <div className="mk-cta__glow" />
      <div className="mk-cta__inner">
        <h2 className="mk-cta__title">
          Connect your
          <br />
          first source.
        </h2>
        <p className="mk-cta__sub">
          Bring a channel and see whether it holds up on its own history — before a cent
          is at risk.
        </p>
        <div className="mk-cta__btns">
          <Button
            as={Link}
            to={signupPath}
            variant="primary"
            size="lg"
            iconRight={<Icon name="arrowRight" size={16} />}
          >
            Sign up
          </Button>
          <Button as={Link} to={loginPath} variant="secondary" size="lg">
            Log in
          </Button>
        </div>
      </div>
    </section>
  )
}

// Links with no page yet render as href-less <a> placeholders (not focusable,
// never navigate) instead of href="#" jumps to the top of the page.
function Footer() {
  const cols = [
    {
      h: 'Product',
      links: [
        ['How it works', '#how'],
        ['Integrations', '#integrations'],
        ['Principles', '#principles']
      ]
    },
    { h: 'Resources', links: [['Docs'], ['Changelog'], ['Status']] },
    { h: 'Company', links: [['About'], ['Contact'], ['Security']] }
  ]
  return (
    <footer className="mk-foot">
      <div className="mk-foot__inner">
        <div className="mk-foot__brand">
          <a className="mk-nav__brand" href="#top">
            <Mark size={24} />
            <span>
              Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
            </span>
          </a>
          <p className="mk-foot__tag">Verify the signal before you trade it.</p>
        </div>
        <div className="mk-foot__cols">
          {cols.map((c) => (
            <div className="mk-foot__col" key={c.h}>
              <div className="mk-foot__h">{c.h}</div>
              {c.links.map(([label, href]) => (
                <a key={label} href={href}>
                  {label}
                </a>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="mk-foot__bar">
        <span>© 2026 Verasig</span>
        <span className="mk-foot__legal">
          <a>Privacy</a>
          <a>Terms</a>
          <a>Security</a>
        </span>
      </div>
    </footer>
  )
}

/* ==================================================== ROOT ===== */
export default function Marketing({ loginPath = '/login', signupPath = '/signup' }) {
  return (
    <div className="mk-page">
      <Nav loginPath={loginPath} signupPath={signupPath} />
      <Hero loginPath={loginPath} signupPath={signupPath} />
      <HowItWorks />
      <Integrations />
      <Principles />
      <CTA loginPath={loginPath} signupPath={signupPath} />
      <Footer />
    </div>
  )
}
