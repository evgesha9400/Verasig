import { useState, useEffect, useRef } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Distill step: backend distills filtering rules from the labels.
   POST /distill starts the job; SSE streams structured stages; GET /rules returns
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

const DISTILL_STAGES = [
  { stage: 'labels_read', phase: 'Reading labels', checklist: 'Labels read' },
  {
    stage: 'filter_distilling',
    phase: 'Distilling filter rules',
    checklist: 'Filter rules'
  },
  {
    stage: 'filter_validating',
    phase: 'Validating against labelled messages',
    checklist: 'Label validation'
  },
  {
    stage: 'parser_distilling',
    phase: 'Distilling parser rules',
    checklist: 'Parser rules'
  },
  { stage: 'rules_persisting', phase: 'Saving ruleset', checklist: 'Ruleset save' },
  { stage: 'rules_complete', phase: 'Ruleset compiled', checklist: 'Complete' }
]
const DISTILL_TOTAL_STEPS = DISTILL_STAGES.length
const DISTILL_STAGE_BY_KEY = new Map(
  DISTILL_STAGES.map((definition, index) => [
    definition.stage,
    { ...definition, step: index + 1 }
  ])
)
const LEGACY_STAGE_BY_PHASE = new Map([
  ['Reading your labelled signals', 'labels_read'],
  ['Extracting structure & tickers', 'filter_distilling'],
  ['Inferring discriminative patterns', 'filter_validating'],
  ['Cross-checking against non-signals', 'parser_distilling'],
  ['Compiling filter ruleset', 'rules_persisting']
])
const INITIAL_PROGRESS = {
  stage: 'labels_read',
  phase: 'Reading labels',
  step: 1,
  totalSteps: DISTILL_TOTAL_STEPS,
  signalLabels: null,
  noiseLabels: null
}

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60)
  const remaining = String(seconds % 60).padStart(2, '0')
  return `${minutes}:${remaining}`
}

function formatLabelCount(count, label) {
  return `${count} ${label} label${count === 1 ? '' : 's'}`
}

function numberOrNull(value) {
  return Number.isFinite(value) ? value : null
}

function normalizeProgressPayload(payload, current) {
  if (!payload) return null
  const legacyStage = LEGACY_STAGE_BY_PHASE.get(payload.phase)
  const stage = payload.stage || legacyStage || current.stage
  const definition = DISTILL_STAGE_BY_KEY.get(stage)
  if (!definition && !payload.phase) return null
  return {
    stage,
    phase: payload.phase || definition?.phase || current.phase,
    step: numberOrNull(payload.step) || definition?.step || current.step,
    totalSteps: numberOrNull(payload.totalSteps) || current.totalSteps,
    signalLabels: numberOrNull(payload.signalLabels) ?? current.signalLabels,
    noiseLabels: numberOrNull(payload.noiseLabels) ?? current.noiseLabels
  }
}

export function DistillView({
  chatId,
  onStartDistill,
  onStreamProgress,
  onGetRules,
  onComplete,
  onError
}) {
  const [phase, setPhase] = useState('thinking') // 'thinking' | 'done' | 'error'
  const [progress, setProgress] = useState(INITIAL_PROGRESS)
  const [lastProgress, setLastProgress] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [rules, setRules] = useState([])
  const [runKey, setRunKey] = useState(0)

  const progressRef = useRef(INITIAL_PROGRESS)
  const lastProgressRef = useRef(null)
  const handlersRef = useRef({
    onStartDistill,
    onStreamProgress,
    onGetRules,
    onError
  })

  useEffect(() => {
    handlersRef.current = { onStartDistill, onStreamProgress, onGetRules, onError }
  }, [onStartDistill, onStreamProgress, onGetRules, onError])

  useEffect(() => {
    if (phase !== 'thinking') return undefined
    const startedAt = Date.now()
    setElapsedSeconds(0)
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [phase])

  useEffect(() => {
    let closed = false
    let subscription = null
    progressRef.current = INITIAL_PROGRESS
    lastProgressRef.current = null
    setProgress(INITIAL_PROGRESS)
    setLastProgress(null)
    setErrorMessage(null)
    setRules([])

    function showRules(compiled) {
      if (closed) return
      setRules(compiled)
      setPhase('done')
    }

    function fail(message) {
      if (closed) return
      const nextMessage = message || 'The distill job did not complete.'
      setErrorMessage(nextMessage)
      setLastProgress(lastProgressRef.current)
      setPhase('error')
      handlersRef.current.onError &&
        handlersRef.current.onError(
          'rejected',
          'Distillation failed',
          nextMessage
        )
    }

    // Read the durable ruleset. An empty ruleset means the job did not really
    // produce rules, so treat it as a failure rather than a "0 rules" success.
    function loadRules(failMessage) {
      Promise.resolve(handlersRef.current.onGetRules(chatId))
        .then((result) => {
          const compiled = result.rules || []
          if (compiled.length === 0) fail(failMessage)
          else showRules(compiled)
        })
        .catch(() => fail(failMessage))
    }

    async function run() {
      try {
        await handlersRef.current.onStartDistill(chatId)
      } catch (error) {
        // A duplicated start (StrictMode / resume) returns 409 — stream the
        // already-running job. Any other start failure is fatal.
        if (error?.status !== 409) {
          fail(error?.message)
          return
        }
      }
      if (closed) return
      subscription = handlersRef.current.onStreamProgress(chatId, {
        onProgress: (payload) => {
          setProgress(
            (current) => {
              const next = normalizeProgressPayload(payload, current) || current
              progressRef.current = next
              lastProgressRef.current = next
              return next
            }
          )
        },
        onDone: () => loadRules('The distill job did not complete.'),
        onError: (payload) => {
          // A named backend error event carries a message → real job failure.
          // A bare connection error ({}) may just mean the finished job was
          // evicted before we connected, so recover from the durable ruleset.
          if (payload && payload.message) fail(payload.message)
          else loadRules('The distill job did not complete.')
        }
      })
    }

    void run()

    return () => {
      closed = true
      subscription && subscription.close()
    }
  }, [chatId, runKey])

  function retryDistillation() {
    progressRef.current = INITIAL_PROGRESS
    lastProgressRef.current = null
    setProgress(INITIAL_PROGRESS)
    setLastProgress(null)
    setErrorMessage(null)
    setElapsedSeconds(0)
    setRules([])
    setPhase('thinking')
    setRunKey((current) => current + 1)
  }

  const activeStepIndex = Math.max(
    0,
    Math.min(DISTILL_STAGES.length - 1, progress.step - 1)
  )
  const labelCounts = [
    numberOrNull(progress.signalLabels) === null
      ? null
      : formatLabelCount(progress.signalLabels, 'signal'),
    numberOrNull(progress.noiseLabels) === null
      ? null
      : formatLabelCount(progress.noiseLabels, 'non-signal')
  ].filter(Boolean)

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
        <div className="vrs-think__status">
          <div className="vrs-think__status-phase">{progress.phase}</div>
          <div className="vrs-think__meta">
            <span>
              Step {progress.step} of {progress.totalSteps}
            </span>
            <span>Elapsed {formatElapsed(elapsedSeconds)}</span>
          </div>
          {labelCounts.length > 0 && (
            <div className="vrs-think__meta">
              {labelCounts.map((count) => (
                <span key={count}>{count}</span>
              ))}
            </div>
          )}
        </div>
        <div className="vrs-think__steps">
          {DISTILL_STAGES.map((definition, i) => (
            <div
              key={definition.stage}
              className={`vrs-think__step ${i < activeStepIndex ? 'is-done' : ''} ${i === activeStepIndex ? 'is-active' : ''}`}
            >
              <span className="vrs-think__tick">
                {i < activeStepIndex ? (
                  <Icon
                    name="check"
                    size={14}
                    style={{ color: 'var(--accent-text)' }}
                  />
                ) : i === activeStepIndex ? (
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
              {definition.checklist}
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
            {errorMessage || 'The distill job did not complete.'}
          </div>
        </div>
        {lastProgress && (
          <div className="vrs-think__status">
            <div className="vrs-think__meta">
              <span>Last progress</span>
              <span>
                Step {lastProgress.step} of {lastProgress.totalSteps}
              </span>
            </div>
            <div className="vrs-think__status-phase">{lastProgress.phase}</div>
          </div>
        )}
        <div className="vrs-form__actions">
          <Button
            variant="primary"
            size="lg"
            iconLeft={<Icon name="refresh" size={16} />}
            onClick={retryDistillation}
          >
            Retry distillation
          </Button>
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
