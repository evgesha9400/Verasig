import { useState, useEffect, useRef, useCallback } from 'react'
import { Badge, Button, IconButton, InteractiveCard, Pill } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { MessageCard } from '../../../shared/components/MessageCard.jsx'

/* Verasig — Verify step: confirm the ruleset's classifications on a fresh sample.
   Samples and their predictions come from GET /chats/{id}/verify/samples; the
   verdicts POST to /chats/{id}/verify, and the BACKEND decides pass/fail. */
const VERIFY_MIN = 6

function VerifyCard({ item, dragX = 0, isTop, style }) {
  const isSignal = item.predicted === 'signal'
  const head = (
    <>
      <Badge tone={isSignal ? 'verified' : 'rejected'} dot>
        {isSignal ? 'Classified: Signal' : 'Classified: Non-signal'}
      </Badge>
      <span className="vrs-card-msg__time" style={{ marginLeft: 'auto' }}>
        auto · rule match
      </span>
    </>
  )
  return (
    <MessageCard
      text={item.text}
      replyTo={item.replyTo}
      media={item.media}
      tone={isSignal ? 'signal' : 'noise'}
      isTop={isTop}
      dragX={dragX}
      style={style}
      stampPositive="Correct"
      stampNegative="Wrong"
      head={head}
    />
  )
}

export function VerifyView({
  chatId,
  onGetSamples,
  onSubmit,
  onPass,
  onStop,
  onLoop,
  onError
}) {
  const [items, setItems] = useState(null) // null while loading
  const [loadError, setLoadError] = useState(false)
  const [idx, setIdx] = useState(0)
  const [marks, setMarks] = useState({}) // id -> 'correct' | 'wrong'
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // { dir, verdict }
  const [result, setResult] = useState(null) // null | 'pass' | 'loop'
  const [submitting, setSubmitting] = useState(false)
  const dragRef = useRef({ active: false, startX: 0 })
  const handlersRef = useRef({ onGetSamples, onSubmit, onError })

  useEffect(() => {
    handlersRef.current = { onGetSamples, onSubmit, onError }
  }, [onGetSamples, onSubmit, onError])

  useEffect(() => {
    let active = true
    setItems(null)
    setLoadError(false)
    setMarks({})
    setResult(null)
    setSubmitting(false)
    Promise.resolve(handlersRef.current.onGetSamples(chatId))
      .then((body) => {
        if (!active) return
        setItems(body.samples || [])
        setIdx(0)
      })
      .catch((error) => {
        if (!active) return
        setLoadError(true)
        handlersRef.current.onError &&
          handlersRef.current.onError(
            'rejected',
            'Could not load samples',
            error?.message || 'Try again.'
          )
      })
    return () => {
      active = false
    }
    // Keyed on chatId only: handlers are accessed via handlersRef so fresh
    // closures from parent re-renders do not restart the load.
  }, [chatId])

  const total = items ? items.length : 0
  const verifiedCount = Object.keys(marks).length
  const correctCount = Object.values(marks).filter((v) => v === 'correct').length
  const flaggedCount = Object.values(marks).filter((v) => v === 'wrong').length
  const minMet = verifiedCount >= VERIFY_MIN

  const commit = useCallback(
    (verdict) => {
      if (!items || idx >= total || flying) return
      const dir = verdict === 'correct' ? 1 : -1
      const id = items[idx].id
      setFlying({ dir, verdict })
      setMarks((m) => ({ ...m, [id]: verdict }))
      setTimeout(() => {
        setFlying(null)
        setDragX(0)
        setIdx((i) => Math.min(total, i + 1))
      }, 300)
    },
    [items, idx, total, flying]
  )

  const goPrev = useCallback(() => {
    if (idx > 0 && !flying) {
      setIdx(idx - 1)
      setDragX(0)
    }
  }, [idx, flying])
  const goNext = useCallback(() => {
    if (idx < total && !flying) {
      setIdx(idx + 1)
      setDragX(0)
    }
  }, [idx, total, flying])

  function finish() {
    if (!minMet || submitting) return
    const verdicts = Object.entries(marks).map(([messageId, verdict]) => ({
      messageId,
      verdict
    }))
    setSubmitting(true)
    Promise.resolve(handlersRef.current.onSubmit(chatId, verdicts))
      .then((body) => {
        setResult(body.passed ? 'pass' : 'loop')
      })
      .catch((error) => {
        handlersRef.current.onError &&
          handlersRef.current.onError(
            'rejected',
            'Could not submit verdicts',
            error?.message || 'Try again.'
          )
      })
      .finally(() => setSubmitting(false))
  }

  useEffect(() => {
    if (result) return
    function onKey(e) {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        commit('correct')
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        commit('wrong')
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        goPrev()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        goNext()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [commit, goPrev, goNext, result])

  function onPointerDown(e) {
    if (!current || flying) return
    dragRef.current = { active: true, startX: e.clientX }
    e.target.setPointerCapture && e.target.setPointerCapture(e.pointerId)
  }
  function onPointerMove(e) {
    if (!dragRef.current.active) return
    setDragX(e.clientX - dragRef.current.startX)
  }
  function onPointerUp() {
    if (!dragRef.current.active) return
    dragRef.current.active = false
    if (dragX > 110) commit('correct')
    else if (dragX < -110) commit('wrong')
    else setDragX(0)
  }

  if (result === 'pass') {
    return (
      <div
        className="vrs-think vrs-think--choice vrs-fade-in"
        style={{ maxWidth: 600 }}
      >
        <span
          className="vrs-rule__ic"
          style={{ width: 64, height: 64, borderRadius: 16 }}
        >
          <Icon name="shield" size={30} />
        </span>
        <div>
          <div className="vrs-think__title">Verification passed</div>
          <div className="vrs-think__sub">
            You confirmed {verifiedCount} of {total} classifications with no errors.
            This source is verified — choose what happens next.
          </div>
        </div>
        <div className="vrs-next">
          <InteractiveCard className="vrs-next-option is-primary" onClick={onStop}>
            <span className="vrs-next-option__ic">
              <Icon name="check" size={20} />
            </span>
            <span className="vrs-next-option__body">
              <span className="vrs-next-option__t">
                Keep it verified
                <Pill tone="accent">Recommended</Pill>
              </span>
              <span className="vrs-next-option__d">
                Save the verified source. You can route it to an exchange and backtest
                later, from the feed&rsquo;s options.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </InteractiveCard>
          <InteractiveCard className="vrs-next-option" onClick={onPass}>
            <span className="vrs-next-option__ic">
              <Icon name="chart" size={20} />
            </span>
            <span className="vrs-next-option__body">
              <span className="vrs-next-option__t">Route &amp; backtest</span>
              <span className="vrs-next-option__d">
                Connect an exchange and simulate the source over its full history.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </InteractiveCard>
        </div>
      </div>
    )
  }
  if (result === 'loop') {
    return (
      <div className="vrs-think vrs-fade-in">
        <span
          className="vrs-rule__ic"
          style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'var(--pending-bg)',
            color: 'var(--pending-500)'
          }}
        >
          <Icon name="refresh" size={28} />
        </span>
        <div>
          <div className="vrs-think__title">{flaggedCount} flagged as wrong</div>
          <div className="vrs-think__sub">
            The ruleset isn&rsquo;t tight enough yet. Label a few more messages so
            Verasig can refine the rules, then we&rsquo;ll verify again.
          </div>
        </div>
        <Button
          variant="primary"
          size="lg"
          iconLeft={<Icon name="arrowLeft" size={16} />}
          onClick={onLoop}
        >
          Back to labelling
        </Button>
      </div>
    )
  }

  const loading = items === null && !loadError
  const empty = !loading && !loadError && total === 0
  const atEnd = !loading && !loadError && !empty && idx >= total
  const current = !loading && !loadError && !empty && !atEnd ? items[idx] : null
  const next1 = !loading && !loadError && !empty && !atEnd ? items[idx + 1] : null

  function renderStage() {
    if (loading) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-dot-pulse" />
          <div className="vrs-rail__note">Loading classifications…</div>
        </div>
      )
    }
    if (loadError) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="alert" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            Couldn&rsquo;t load samples
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            Something went wrong. Go back and try again.
          </div>
        </div>
      )
    }
    if (empty) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="signals" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            Nothing to verify
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            There are no unreviewed classifications for this feed.
          </div>
        </div>
      )
    }
    if (atEnd) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="check" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            All classifications reviewed
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            {verifiedCount} of {total} verified. Press <kbd className="vrs-kbd">↑</kbd>{' '}
            to revisit, or finish verification.
          </div>
        </div>
      )
    }
    return (
      <>
        {next1 && (
          <VerifyCard
            key={'bg' + next1.id}
            item={next1}
            isTop={false}
            style={{ transform: 'scale(0.95) translateY(14px)', opacity: 0.6 }}
          />
        )}
        <VerifyCard
          key={current.id}
          item={current}
          isTop={true}
          dragX={flying ? flying.dir * 600 : dragX}
          style={
            flying
              ? {
                  transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
                  transform: `translateX(${flying.dir * 600}px) rotate(${flying.dir * 18}deg)`
                }
              : dragRef.current.active
                ? {}
                : { transition: 'transform 0.25s var(--ease-out)' }
          }
        />
      </>
    )
  }

  return (
    <div className="vrs-label">
      <div className="vrs-deck">
        <div className="vrs-deck__viewport">
          <div
            className="vrs-deck__stage"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            style={{
              cursor: current ? (dragRef.current.active ? 'grabbing' : 'grab') : 'default'
            }}
          >
            {renderStage()}
          </div>
        </div>

        <div className="vrs-swipe-controls">
          <IconButton
            variant="solid"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--no"
            label="Misclassified"
            onClick={() => commit('wrong')}
            disabled={atEnd || loading || empty || loadError}
            title="Misclassified (←)"
          >
            <Icon name="x" size={22} />
          </IconButton>
          <div className="vrs-deck__nav">
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Previous"
              onClick={goPrev}
              disabled={idx === 0}
              title="Previous (↑)"
            >
              <Icon name="arrowUp" size={18} />
            </IconButton>
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Skip"
              onClick={goNext}
              disabled={atEnd || loading || empty || loadError}
              title="Skip (↓)"
            >
              <Icon name="arrowDown" size={18} />
            </IconButton>
          </div>
          <IconButton
            variant="accent"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--yes"
            label="Correct"
            onClick={() => commit('correct')}
            disabled={atEnd || loading || empty || loadError}
            title="Correct (→)"
          >
            <Icon name="check" size={22} />
          </IconButton>
        </div>
        <div className="vrs-deck__hint">
          <kbd>←</kbd> Misclassified &nbsp;·&nbsp; <kbd>→</kbd> Correct &nbsp;·&nbsp;{' '}
          <kbd>↑</kbd> Back &nbsp;·&nbsp; <kbd>↓</kbd> Skip
        </div>
      </div>

      <div className="vrs-rail">
        <div className="vrs-rail__h">Verify classification</div>
        <div className="vrs-rail__note">
          Verasig classified every message. Swipe right to confirm a call is correct,
          left to flag a misclassification. Any flag sends the rules back to refine.
        </div>

        <div className="vrs-rail__counts">
          <div className="vrs-count-card signal">
            <div className="vrs-count-card__v">{correctCount}</div>
            <div className="vrs-count-card__l">Correct</div>
          </div>
          <div className="vrs-count-card noise">
            <div className="vrs-count-card__v">{flaggedCount}</div>
            <div className="vrs-count-card__l">Flagged</div>
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Verified</span>
            <span>
              {verifiedCount} / {total}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${total ? (verifiedCount / total) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Minimum sample</span>
            <span>
              {Math.min(verifiedCount, VERIFY_MIN)} / {VERIFY_MIN}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span
              style={{ width: `${Math.min(verifiedCount / VERIFY_MIN, 1) * 100}%` }}
            />
          </div>
        </div>

        <div className="vrs-rail__done">
          <Button
            variant="primary"
            fullWidth
            disabled={!minMet || submitting}
            loading={submitting}
            onClick={finish}
            iconLeft={<Icon name={flaggedCount > 0 ? 'refresh' : 'shield'} size={16} />}
          >
            {!minMet
              ? `Verify ${VERIFY_MIN - verifiedCount} more`
              : flaggedCount > 0
                ? 'Refine rules'
                : 'Finish verification'}
          </Button>
          <div
            className="vrs-rail__note"
            style={{ marginTop: 10, textAlign: 'center' }}
          >
            {!minMet
              ? `Confirm at least ${VERIFY_MIN} classifications to continue.`
              : flaggedCount > 0
                ? `${flaggedCount} flagged — we'll refine the rules and re-verify.`
                : 'Keep going or finish — extra checks tighten confidence.'}
          </div>
        </div>
      </div>
    </div>
  )
}

const STAGE_CENTER = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  textAlign: 'center',
  padding: 30
}
