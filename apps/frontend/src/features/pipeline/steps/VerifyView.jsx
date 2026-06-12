import { useState, useEffect, useRef, useCallback } from 'react'
import { Badge, Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { MESSAGES, VERIFY_MIN, VERIFY_MISCLASSIFIED } from '../../../data/seed.js'

/* Verasig prototype — Verify step: confirm the ruleset's classifications.
   Same swipe interface as Label: ← / → give a verdict, ↑ / ↓ navigate.
   The user reviews every message the ruleset classified — both Signal and
   Non-signal — and must verify at least VERIFY_MIN before continuing, but is
   free to verify as many as they like. */

function VerifyMedia({ kind }) {
  const map = {
    chart: ['chart', 'Chart screenshot'],
    image: ['image', 'Image'],
    doc: ['doc', 'Document']
  }
  const [icon, label] = map[kind] || ['image', 'Attachment']
  return (
    <div className="vrs-card-msg__media">
      <Icon name={icon} />
      <span>{label}</span>
    </div>
  )
}

function VerifyCard({ item, dragX = 0, isTop, style }) {
  const rot = dragX / 22
  const tStyle = isTop
    ? { transform: `translateX(${dragX}px) rotate(${rot}deg)`, ...style }
    : style
  const isSignal = item.predicted === 'signal'
  const isMod = item.predicted === 'modifier'
  const cls = `vrs-card-msg ${isSignal ? 'is-signal' : isMod ? 'is-mod' : 'is-noise'}`
  return (
    <div className={cls} style={tStyle}>
      {isTop && (
        <>
          <span
            className="vrs-card-stamp signal"
            style={{ opacity: Math.max(0, Math.min(1, dragX / 90)) }}
          >
            Correct
          </span>
          <span
            className="vrs-card-stamp noise"
            style={{ opacity: Math.max(0, Math.min(1, -dragX / 90)) }}
          >
            Wrong
          </span>
        </>
      )}
      <div className="vrs-card-msg__head">
        <Badge tone={isSignal ? 'verified' : isMod ? 'info' : 'rejected'} dot>
          {isSignal
            ? 'Classified: Signal'
            : isMod
              ? 'Classified: Update'
              : 'Classified: Non-signal'}
        </Badge>
        <span className="vrs-card-msg__time" style={{ marginLeft: 'auto' }}>
          auto · rule match
        </span>
      </div>
      <div className="vrs-card-msg__body">
        {item.replyTo && (
          <div className="vrs-card-reply">
            <Icon name="reply" size={12} />
            <span className="vrs-card-reply__body">
              <span className="vrs-card-reply__who">{item.replyTo.author}</span>
              <span className="vrs-card-reply__txt">{item.replyTo.text}</span>
            </span>
          </div>
        )}
        <div className="vrs-card-msg__text">{item.text}</div>
        {item.media && <VerifyMedia kind={item.media} />}
        {isMod && item.mod && (
          <div className="vrs-vparse">
            <div className="vrs-vparse__row">
              <span className="vrs-vparse__k">Parsed action</span>
              <span className="vrs-vparse__v">{item.mod.label}</span>
            </div>
            <div className="vrs-vparse__row">
              <span className="vrs-vparse__k">Applies to</span>
              <span className="vrs-vparse__v">
                <Icon name={item.mod.via === 'reply' ? 'reply' : 'link'} size={11} />{' '}
                {item.mod.target}
              </span>
            </div>
            <div className="vrs-vparse__via">
              {item.mod.via === 'reply'
                ? 'Linked via reply — authoritative'
                : 'Link inferred — no reply on the message'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function VerifyView({ attempt, onPass, onStop, onLoop }) {
  // Every backfilled message, tagged with the ruleset's prediction. Earlier
  // attempts contain genuine misclassifications the user should catch.
  const items = (() => {
    const flips = VERIFY_MISCLASSIFIED[attempt] || {}
    return MESSAGES.map((m) => ({ ...m, predicted: flips[m.id] || m.truth }))
  })()

  const total = items.length
  const [idx, setIdx] = useState(0)
  const [marks, setMarks] = useState({}) // id -> 'correct' | 'wrong'
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // { dir, verdict }
  const [result, setResult] = useState(null) // null | 'pass' | 'loop'
  const dragRef = useRef({ active: false, startX: 0 })

  const verifiedCount = Object.keys(marks).length
  const correctCount = Object.values(marks).filter((v) => v === 'correct').length
  const flaggedCount = Object.values(marks).filter((v) => v === 'wrong').length
  const minMet = verifiedCount >= VERIFY_MIN

  const commit = useCallback(
    (verdict) => {
      if (idx >= total || flying) return
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
    [idx, total, flying, items]
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
    if (!minMet) return
    setResult(flaggedCount > 0 ? 'loop' : 'pass')
  }

  // keyboard — identical mapping to Label
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

  // pointer drag
  function onPointerDown(e) {
    if (idx >= total || flying) return
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

  // ---- result screens ----
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
            You confirmed {verifiedCount} of {total} classifications with no errors. We
            extracted every matching signal from the feed history — choose what happens
            next.
          </div>
        </div>
        <div className="vrs-next">
          <button className="vrs-next-card is-primary" onClick={onPass}>
            <span className="vrs-next-card__ic">
              <Icon name="chart" size={20} />
            </span>
            <span className="vrs-next-card__body">
              <span className="vrs-next-card__t">
                Connect an exchange &amp; backtest
                <span className="vrs-next-tag">Recommended</span>
              </span>
              <span className="vrs-next-card__d">
                Route verified signals to an exchange and simulate the source over its
                full history for a quality score and win rate.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </button>
          <button className="vrs-next-card" onClick={onStop}>
            <span className="vrs-next-card__ic">
              <Icon name="check" size={20} />
            </span>
            <span className="vrs-next-card__body">
              <span className="vrs-next-card__t">Stop here — keep it verified</span>
              <span className="vrs-next-card__d">
                Save the verified source without connecting an exchange or backtesting.
                You can backtest later, any time, from the feed’s options.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </button>
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
            The ruleset isn’t tight enough yet. Label a few more messages so Verasig can
            refine the rules, then we’ll verify again.
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

  // ---- review deck ----
  const atEnd = idx >= total
  const current = !atEnd ? items[idx] : null
  const next1 = !atEnd ? items[idx + 1] : null

  return (
    <div className="vrs-label">
      <div className="vrs-deck">
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
          {atEnd ? (
            <div
              className="vrs-card-bg"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                textAlign: 'center',
                padding: 30
              }}
            >
              <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
                <Icon name="check" size={20} />
              </span>
              <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
                All classifications reviewed
              </div>
              <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
                {verifiedCount} of {total} verified. Press{' '}
                <kbd className="vrs-kbd">↑</kbd> to revisit, or finish verification.
              </div>
            </div>
          ) : (
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
          )}
        </div>

        <div className="vrs-swipe-controls">
          <button
            className="vrs-swipe-btn no"
            onClick={() => commit('wrong')}
            disabled={atEnd}
            title="Misclassified (←)"
          >
            <Icon name="x" size={22} />
          </button>
          <div className="vrs-deck__nav">
            <button
              className="vrs-swipe-btn nav"
              onClick={goPrev}
              disabled={idx === 0}
              title="Previous (↑)"
            >
              <Icon name="arrowUp" size={18} />
            </button>
            <button
              className="vrs-swipe-btn nav"
              onClick={goNext}
              disabled={atEnd}
              title="Skip (↓)"
            >
              <Icon name="arrowDown" size={18} />
            </button>
          </div>
          <button
            className="vrs-swipe-btn yes"
            onClick={() => commit('correct')}
            disabled={atEnd}
            title="Correct (→)"
          >
            <Icon name="check" size={22} />
          </button>
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
          left to flag a misclassification. On updates, also check the parsed action and
          the signal it’s linked to. Any flag sends the rules back to refine.
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
            <span style={{ width: `${(verifiedCount / total) * 100}%` }} />
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
            disabled={!minMet}
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
                ? `${flaggedCount} flagged — we’ll refine the rules and re-verify.`
                : 'Keep going or finish — extra checks tighten confidence.'}
          </div>
        </div>
      </div>
    </div>
  )
}
