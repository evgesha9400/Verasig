import { useState, useEffect, useRef, useCallback } from 'react'
import { Button, IconButton } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Label step: Tinder-style signal / non-signal classification.
   Labeling is BINARY on purpose: a reply that is a signal is, by definition, an
   update (close / average / move stop) to the signal it quotes — Verasig derives
   that from the reply link, the user doesn't label it separately. The reply
   context is shown on the card; the parsed action gets confirmed at Verify.

   Data is backend-owned: the deck is the unlabeled candidate messages from
   GET /chats/{id}/messages; each swipe persists with POST .../label; the rail
   counts are seeded from GET /chats/{id}/labels and bumped locally. */
function MsgMedia({ kind }) {
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

function MessageCard({ msg, label, dragX = 0, isTop, style }) {
  const rot = dragX / 22
  const cls = `vrs-card-msg ${label === 'signal' ? 'is-signal' : ''} ${label === 'noise' ? 'is-noise' : ''}`
  const tStyle = isTop
    ? { transform: `translateX(${dragX}px) rotate(${rot}deg)`, ...style }
    : style
  return (
    <div className={cls} style={tStyle}>
      {isTop && (
        <>
          <span
            className="vrs-card-stamp signal"
            style={{ opacity: Math.max(0, Math.min(1, dragX / 90)) }}
          >
            Signal
          </span>
          <span
            className="vrs-card-stamp noise"
            style={{ opacity: Math.max(0, Math.min(1, -dragX / 90)) }}
          >
            Noise
          </span>
        </>
      )}
      <div className="vrs-card-msg__head">
        <span className="vrs-card-msg__av" style={{ background: 'var(--viz-2)' }}>
          {(msg.author || 'AC').slice(0, 2).toUpperCase()}
        </span>
        <span className="vrs-card-msg__who">{msg.author || 'Apex'}</span>
        {msg.replyTo && (
          <span className="vrs-autolink">
            <Icon name="reply" size={11} /> reply
          </span>
        )}
        <span className="vrs-card-msg__time">
          {msg.date} · {msg.time}
        </span>
      </div>
      <div className="vrs-card-msg__body">
        {msg.replyTo && (
          <div className="vrs-card-reply">
            <Icon name="reply" size={12} />
            <span className="vrs-card-reply__body">
              <span className="vrs-card-reply__who">{msg.replyTo.author}</span>
              <span className="vrs-card-reply__txt">{msg.replyTo.text}</span>
            </span>
          </div>
        )}
        <div className="vrs-card-msg__text">{msg.text}</div>
        {msg.media && <MsgMedia kind={msg.media} />}
      </div>
    </div>
  )
}

export function LabelView({
  chatId,
  onListMessages,
  onGetCounts,
  onRecordLabel,
  onDistill,
  onError
}) {
  const [messages, setMessages] = useState(null) // null while loading
  const [loadError, setLoadError] = useState(false)
  const [baseCounts, setBaseCounts] = useState({ signalCount: 0, noiseCount: 0 })
  const [labels, setLabels] = useState({}) // session map: msgId -> 'signal' | 'noise'
  const [idx, setIdx] = useState(0)
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // {dir, label}
  const dragRef = useRef({ active: false, startX: 0 })
  const handlersRef = useRef({ onListMessages, onGetCounts, onRecordLabel, onError })

  useEffect(() => {
    handlersRef.current = { onListMessages, onGetCounts, onRecordLabel, onError }
  }, [onListMessages, onGetCounts, onRecordLabel, onError])

  useEffect(() => {
    let active = true
    setMessages(null)
    setLoadError(false)
    Promise.all([
      handlersRef.current.onListMessages(chatId),
      handlersRef.current.onGetCounts(chatId)
    ])
      .then(([messagesResult, counts]) => {
        if (!active) return
        setMessages(messagesResult.messages || [])
        setBaseCounts({
          signalCount: counts.signalCount || 0,
          noiseCount: counts.noiseCount || 0
        })
        setLabels({})
        setIdx(0)
      })
      .catch((error) => {
        if (!active) return
        setLoadError(true)
        handlersRef.current.onError &&
          handlersRef.current.onError(
            'rejected',
            'Could not load messages',
            error?.message || 'Try again.'
          )
      })
    return () => {
      active = false
    }
    // Keyed on chatId only: handlers are accessed via handlersRef so fresh
    // closures from parent re-renders do not restart the load.
  }, [chatId])

  const total = messages ? messages.length : 0
  const localSignal = Object.values(labels).filter((value) => value === 'signal').length
  const localNoise = Object.values(labels).filter((value) => value === 'noise').length
  const signalCount = baseCounts.signalCount + localSignal
  const noiseCount = baseCounts.noiseCount + localNoise
  const labeledCount = localSignal + localNoise
  const canDistill = signalCount >= 5
  const updateCount = (messages || []).filter(
    (m) => m.replyTo && labels[m.id] === 'signal'
  ).length

  const commit = useCallback(
    (label) => {
      if (!messages || idx >= total || flying) return
      const message = messages[idx]
      const dir = label === 'signal' ? 1 : -1
      const previous = labels[message.id]
      setFlying({ dir, label })
      setLabels((current) => ({ ...current, [message.id]: label }))
      Promise.resolve(
        handlersRef.current.onRecordLabel(chatId, message.id, label)
      ).catch((error) => {
        setLabels((current) => {
          const next = { ...current }
          if (previous === undefined) delete next[message.id]
          else next[message.id] = previous
          return next
        })
        handlersRef.current.onError &&
          handlersRef.current.onError(
            'rejected',
            'Label not saved',
            error?.message || 'Try again.'
          )
      })
      setTimeout(() => {
        setFlying(null)
        setDragX(0)
        setIdx((i) => Math.min(total, i + 1))
      }, 300)
    },
    [messages, idx, total, flying, labels, chatId]
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

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        commit('signal')
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        commit('noise')
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
  }, [commit, goPrev, goNext])

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
    if (dragX > 110) commit('signal')
    else if (dragX < -110) commit('noise')
    else setDragX(0)
  }

  const loading = messages === null && !loadError
  const empty = !loading && !loadError && total === 0
  const atEnd = !loading && !loadError && !empty && idx >= total
  const current = !loading && !loadError && !empty && !atEnd ? messages[idx] : null
  const next1 = !loading && !loadError && !empty && !atEnd ? messages[idx + 1] : null

  function renderStage() {
    if (loading) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-dot-pulse" />
          <div className="vrs-rail__note">Loading messages…</div>
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
            Couldn&rsquo;t load messages
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
            No messages to label
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            This feed has no candidate signals to review yet.
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
            Sample reviewed
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            {labeledCount} of {total} labelled. Press <kbd className="vrs-kbd">↑</kbd>{' '}
            to revisit, or distill rules from your signals.
          </div>
        </div>
      )
    }
    return (
      <>
        {next1 && (
          <MessageCard
            key={'bg' + next1.id}
            msg={next1}
            label={labels[next1.id]}
            isTop={false}
            style={{ transform: 'scale(0.95) translateY(14px)', opacity: 0.6 }}
          />
        )}
        <MessageCard
          key={current.id}
          msg={current}
          label={labels[current.id]}
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

        <div className="vrs-swipe-controls">
          <IconButton
            variant="solid"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--no"
            label="Non-signal"
            onClick={() => commit('noise')}
            disabled={atEnd || loading || empty || loadError}
            title="Non-signal (←)"
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
              label="Next"
              onClick={goNext}
              disabled={atEnd || loading || empty || loadError}
              title="Next (↓)"
            >
              <Icon name="arrowDown" size={18} />
            </IconButton>
          </div>
          <IconButton
            variant="accent"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--yes"
            label="Signal"
            onClick={() => commit('signal')}
            disabled={atEnd || loading || empty || loadError}
            title="Signal (→)"
          >
            <Icon name="check" size={22} />
          </IconButton>
        </div>
        <div className="vrs-deck__hint">
          <kbd>←</kbd> Non-signal &nbsp;·&nbsp; <kbd>→</kbd> Signal &nbsp;·&nbsp;{' '}
          <kbd>↑</kbd> Back &nbsp;·&nbsp; <kbd>↓</kbd> Skip
        </div>
      </div>

      <div className="vrs-rail">
        <div className="vrs-rail__h">Label messages</div>
        <div className="vrs-rail__note">
          Swipe right for trade signals, left for chatter, promos and noise. A signal
          that replies to an earlier signal is treated as an update to it — closes,
          averages and stop moves included.
        </div>

        <div className="vrs-rail__counts">
          <div className="vrs-count-card signal">
            <div className="vrs-count-card__v">{signalCount}</div>
            <div className="vrs-count-card__l">Signal</div>
          </div>
          <div className="vrs-count-card noise">
            <div className="vrs-count-card__v">{noiseCount}</div>
            <div className="vrs-count-card__l">Non-signal</div>
          </div>
        </div>

        {updateCount > 0 && (
          <div className="vrs-rail__derived">
            <Icon name="reply" size={13} />
            <span>
              <strong>{updateCount}</strong> of your signals{' '}
              {updateCount === 1 ? 'is a reply' : 'are replies'} — they&rsquo;ll be
              linked to the signal they quote as updates, not opened as new positions.
            </span>
          </div>
        )}

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Reviewed</span>
            <span>
              {labeledCount} / {total}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${total ? (labeledCount / total) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Signals to distill</span>
            <span>{Math.min(signalCount, 5)} / 5</span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${Math.min(signalCount / 5, 1) * 100}%` }} />
          </div>
        </div>

        <div className="vrs-rail__done">
          <Button
            variant="primary"
            fullWidth
            disabled={!canDistill}
            onClick={onDistill}
            iconLeft={<Icon name="sparkles" size={16} />}
          >
            {canDistill
              ? 'Distill rules'
              : `Label ${5 - signalCount} more signal${5 - signalCount === 1 ? '' : 's'}`}
          </Button>
          {!canDistill && (
            <div
              className="vrs-rail__note"
              style={{ marginTop: 10, textAlign: 'center' }}
            >
              Distillation unlocks at 5 labelled signals.
            </div>
          )}
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
