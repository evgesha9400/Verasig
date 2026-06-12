import { useState, useEffect } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { DISTILLED_RULES } from '../../../data/seed.js'

/* Verasig prototype — Distill step: AI generates filtering rules */
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

export function DistillView({ onComplete }) {
  const [phase, setPhase] = useState('thinking')
  const [step, setStep] = useState(0)

  const steps = [
    'Reading your labelled signals',
    'Extracting structure & tickers',
    'Inferring discriminative patterns',
    'Cross-checking against non-signals',
    'Compiling filter ruleset'
  ]

  useEffect(() => {
    if (phase !== 'thinking') return
    if (step < steps.length) {
      const t = setTimeout(() => setStep(step + 1), 720)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => setPhase('done'), 500)
    return () => clearTimeout(t)
  }, [phase, step])

  if (phase === 'thinking') {
    return (
      <div className="vrs-think vrs-fade-in">
        <ThinkOrb />
        <div>
          <div className="vrs-think__title">Distilling signal rules</div>
          <div className="vrs-think__sub">
            Verasig is analysing your labels to learn what makes a message a tradeable
            signal.
          </div>
        </div>
        <div className="vrs-think__steps">
          {steps.map((s, i) => (
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
    <div className="vrs-page vrs-fade-in" style={{ maxWidth: 720 }}>
      <div className="vrs-setup__hero" style={{ alignItems: 'flex-start' }}>
        <span
          className="vrs-rule__ic"
          style={{ width: 44, height: 44, borderRadius: 10 }}
        >
          <Icon name="sparkles" size={22} />
        </span>
        <div>
          <div className="vrs-setup__title" style={{ fontSize: 'var(--text-xl)' }}>
            5 rules distilled
          </div>
          <div className="vrs-setup__sub">
            These rules now classify the rest of the feed history. Verify a random
            sample below before we extract.
          </div>
        </div>
      </div>

      <div className="vrs-rules">
        {DISTILLED_RULES.map((r, i) => (
          <div
            key={r.id}
            className="vrs-rule vrs-fade-in"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <span className="vrs-rule__ic">
              <Icon name="check" size={15} />
            </span>
            <div>
              <div className="vrs-rule__lbl">{r.label}</div>
              <div className="vrs-rule__detail">{r.detail}</div>
            </div>
            <span className="vrs-rule__match">{Math.round(r.match * 100)}%</span>
          </div>
        ))}
      </div>

      <div className="vrs-form__actions">
        <Button
          variant="primary"
          size="lg"
          iconRight={<Icon name="arrowRight" size={16} />}
          onClick={onComplete}
        >
          Verify on new messages
        </Button>
      </div>
    </div>
  )
}
