import { useState, useEffect } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Distill step: backend distills filtering rules from the labels.
   POST /distill starts the job; SSE streams the five phases; GET /rules returns
   the compiled ruleset (match is already a 0–100 percentage). */
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

/* Must match the backend DISTILL_PHASES strings exactly (distill_routes.py). */
const DISTILL_STEPS = [
  'Reading your labelled signals',
  'Extracting structure & tickers',
  'Inferring discriminative patterns',
  'Cross-checking against non-signals',
  'Compiling filter ruleset'
]

export function DistillView({
  chatId,
  onStartDistill,
  onStreamProgress,
  onGetRules,
  onComplete,
  onError
}) {
  const [phase, setPhase] = useState('thinking') // 'thinking' | 'done' | 'error'
  const [step, setStep] = useState(0)
  const [rules, setRules] = useState([])

  // No start-once ref: mirror BackfillView. In React StrictMode the effect runs
  // twice; the first run's cleanup sets closed=true (so it never subscribes) and
  // the second run re-POSTs. A duplicate POST returns 409, which we tolerate and
  // stream the already-running job. In production the effect runs once.
  useEffect(() => {
    let closed = false
    let subscription = null

    function loadRules() {
      return Promise.resolve(onGetRules(chatId)).then((result) => {
        if (closed) return
        setRules(result.rules || [])
        setPhase('done')
      })
    }

    function fail() {
      if (closed) return
      setPhase('error')
      onError &&
        onError('rejected', 'Distillation failed', 'The distill job did not complete.')
    }

    async function run() {
      try {
        await onStartDistill(chatId)
      } catch (error) {
        // A duplicated start (StrictMode / resume) is fine — stream the running job.
        if (error?.status !== 409) {
          if (!closed) {
            setPhase('error')
            onError &&
              onError('rejected', 'Distillation failed', error?.message || 'Try again.')
          }
          return
        }
      }
      if (closed) return
      subscription = onStreamProgress(chatId, {
        onProgress: (progress) => {
          if (!progress.phase) return
          const index = DISTILL_STEPS.indexOf(progress.phase)
          if (index >= 0) setStep(index + 1)
        },
        // On done OR on a stream error, read the durable ruleset. The job may have
        // finished and been evicted before we connected (distill has no replay),
        // so reading /rules is the source of truth; only fail if that read fails.
        onDone: () => {
          loadRules().catch(fail)
        },
        onError: () => {
          loadRules().catch(fail)
        }
      })
    }

    void run()

    return () => {
      closed = true
      subscription && subscription.close()
    }
  }, [chatId, onStartDistill, onStreamProgress, onGetRules, onError])

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
          {DISTILL_STEPS.map((s, i) => (
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

  if (phase === 'error') {
    return (
      <div className="vrs-think vrs-fade-in" style={{ maxWidth: 520 }}>
        <span
          className="vrs-rule__ic"
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            background: 'var(--rejected-bg)',
            color: 'var(--rejected-500)'
          }}
        >
          <Icon name="alert" size={26} />
        </span>
        <div>
          <div className="vrs-think__title">Distillation didn&apos;t complete</div>
          <div className="vrs-think__sub">
            Something interrupted the distill job. Go back and try again.
          </div>
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
            {rules.length} rule{rules.length === 1 ? '' : 's'} distilled
          </div>
          <div className="vrs-setup__sub">
            These rules now classify the rest of the feed history. Verify a random
            sample below before we extract.
          </div>
        </div>
      </div>

      <div className="vrs-rules">
        {rules.map((r, i) => (
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
            <span className="vrs-rule__match">{Math.round(r.match)}%</span>
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
