import { useState, useEffect } from 'react'
import { Button, MetricStat, ConfidenceBar, Card } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig prototype — Backtest run + signal quality results */
function ThinkOrb() {
  return (
    <svg className="vrs-think__orb" viewBox="0 0 86 86" fill="none">
      <circle cx="43" cy="43" r="30" stroke="var(--border-strong)" strokeWidth="1.5" />
      <circle
        cx="43"
        cy="43"
        r="30"
        stroke="var(--signal-500)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeDasharray="48 140"
        style={{ filter: 'drop-shadow(0 0 5px var(--signal-glow))' }}
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 43 43"
          to="360 43 43"
          dur="1.1s"
          repeatCount="indefinite"
        />
      </circle>
      <path
        d="M28 43 L37 43 L41 33 L46 53 L50 43 L58 43"
        stroke="var(--signal-500)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const BACKTEST_STEPS = [
  'Replaying 12,840 historical signals',
  'Applying your risk model',
  'Simulating fills & slippage',
  'Scoring confidence & drawdown'
]

function ScoreRing({ value, size = 132 }) {
  const r = (size - 16) / 2
  const c = 2 * Math.PI * r
  const off = c * (1 - value / 100)
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="vrs-bt-ring"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke="var(--surface-raised)"
        strokeWidth="8"
        fill="none"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke="var(--signal-500)"
        strokeWidth="8"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={off}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{
          filter: 'drop-shadow(0 0 6px var(--signal-glow))',
          transition: 'stroke-dashoffset 1.2s var(--ease-out)'
        }}
      />
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dy="0.05em"
        fontFamily="var(--font-mono)"
        fontSize={size * 0.3}
        fontWeight="300"
        fill="var(--text-strong)"
      >
        {value}
      </text>
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dy="2.1em"
        fontFamily="var(--font-mono)"
        fontSize="10"
        letterSpacing="0.14em"
        fill="var(--text-faint)"
      >
        / 100
      </text>
    </svg>
  )
}

export function BacktestView({ chat, onComplete, skipRun = false }) {
  const [phase, setPhase] = useState(skipRun ? 'done' : 'running')
  const [step, setStep] = useState(skipRun ? 4 : 0)
  const score = (skipRun && chat.score) || 88,
    winRate = (skipRun && chat.winRate) || 66.4,
    pnl = (skipRun && chat.pnl) || 47.3

  useEffect(() => {
    if (phase !== 'running') return
    if (step < BACKTEST_STEPS.length) {
      const t = setTimeout(() => setStep(step + 1), 820)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => setPhase('done'), 600)
    return () => clearTimeout(t)
  }, [phase, step])

  if (phase === 'running') {
    return (
      <div className="vrs-think vrs-fade-in">
        <ThinkOrb />
        <div>
          <div className="vrs-think__title">Running backtest</div>
          <div className="vrs-think__sub">
            Simulating how {chat.name}’s verified signals would have performed with your
            risk settings.
          </div>
        </div>
        <div className="vrs-think__steps">
          {BACKTEST_STEPS.map((s, i) => (
            <div
              key={i}
              className={`vrs-think__step ${i < step ? 'is-done' : ''} ${i === step ? 'is-active' : ''}`}
            >
              <span className="vrs-think__tick">
                {i < step ? (
                  <Icon
                    name="check"
                    size={14}
                    style={{ color: 'var(--accent-text)' }}
                  />
                ) : i === step ? (
                  <span className="vrs-dot-pulse" />
                ) : (
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      border: '1px solid var(--border-strong)'
                    }}
                  />
                )}
              </span>
              {s}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="vrs-page vrs-fade-in" style={{ maxWidth: 880 }}>
      <div className="vrs-bt-hero">
        <ScoreRing value={score} />
        <div className="vrs-bt-hero__txt">
          <div className="vrs-sec-t">Signal quality score</div>
          <div
            className="vrs-setup__title"
            style={{ fontSize: 'var(--text-2xl)', marginTop: 6 }}
          >
            High-confidence source
          </div>
          <div className="vrs-setup__sub" style={{ maxWidth: '48ch' }}>
            {chat.name} verified clean across the sample with strong risk-adjusted
            returns. Ready to route live when you are.
          </div>
          <div style={{ marginTop: 16, maxWidth: 380 }}>
            <ConfidenceBar value={score} threshold={70} label="Quorum" />
          </div>
        </div>
      </div>

      <div className="vrs-bt-grid">
        <Card>
          <MetricStat
            label="Win rate"
            value={winRate}
            unit="%"
            delta="+4.2"
            trend="up"
            caption="847 of 1,275 trades"
          />
        </Card>
        <Card>
          <MetricStat
            label="Net PnL"
            value={`+${pnl}`}
            unit="%"
            delta="+12.6"
            trend="up"
            caption="Compounded, 6 mo"
          />
        </Card>
        <Card>
          <MetricStat
            label="Max drawdown"
            value="14.8"
            unit="%"
            delta="−2.1"
            trend="up"
            caption="Peak to trough"
          />
        </Card>
        <Card>
          <MetricStat
            label="Avg latency"
            value="1.9"
            unit="s"
            caption="Signal → order"
          />
        </Card>
      </div>

      <div className="vrs-row-between" style={{ marginTop: 4 }}>
        <div className="vrs-rail__note" style={{ maxWidth: '46ch' }}>
          This source is verified and saved. Nothing routes to Bybit yet — you can
          re-backfill, adjust risk, or go live whenever you’re ready.
        </div>
        <Button
          variant="primary"
          size="lg"
          iconLeft={<Icon name="check" size={16} />}
          onClick={() => onComplete({ score, winRate, pnl })}
        >
          Finish
        </Button>
      </div>
    </div>
  )
}
