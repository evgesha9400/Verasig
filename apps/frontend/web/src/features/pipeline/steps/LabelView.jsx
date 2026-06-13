import { useState, useEffect, useRef, useCallback } from 'react'
import { Button, IconButton } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig prototype — Label step: Tinder-style signal / non-signal classification.
   Labeling is BINARY on purpose: a reply that is a signal is, by definition, an
   update (close / average / move stop) to the signal it quotes — Verasig derives
   that from the reply link, the user doesn't label it separately. The reply
   context is shown on the card; the parsed action gets confirmed at Verify. */
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
  messages,
  labels,
  onLabel,
  signalCount,
  noiseCount,
  onDistill
}) {
  const [idx, setIdx] = useState(() => {
    const firstUnlabeled = messages.findIndex((m) => !labels[m.id])
    return firstUnlabeled === -1 ? messages.length : firstUnlabeled
  })
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // {dir, label}
  const dragRef = useRef({ active: false, startX: 0 })

  const total = messages.length
  const labeledCount = signalCount + noiseCount
  const canDistill = signalCount >= 5
  // Replies the user marked as signals — Verasig will treat these as updates
  // to the signal they quote (close / average / move stop), not new positions.
  const updateCount = messages.filter(
    (m) => m.replyTo && (labels[m.id] === 'signal' || labels[m.id] === 'modifier')
  ).length

  const commit = useCallback(
    (label) => {
      if (idx >= total || flying) return
      const dir = label === 'signal' ? 1 : -1
      setFlying({ dir, label })
      onLabel(messages[idx].id, label)
      setTimeout(() => {
        setFlying(null)
        setDragX(0)
        setIdx((i) => Math.min(total, i + 1))
      }, 300)
    },
    [idx, total, flying, messages, onLabel]
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

  // keyboard
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
    if (dragX > 110) commit('signal')
    else if (dragX < -110) commit('noise')
    else setDragX(0)
  }

  const atEnd = idx >= total
  const current = !atEnd ? messages[idx] : null
  const next1 = !atEnd ? messages[idx + 1] : null

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
                Sample reviewed
              </div>
              <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
                {labeledCount} of {total} labelled. Press{' '}
                <kbd className="vrs-kbd">↑</kbd> to revisit, or distill rules from your
                signals.
              </div>
            </div>
          ) : (
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
          )}
        </div>

        <div className="vrs-swipe-controls">
          <IconButton
            variant="solid"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--no"
            label="Non-signal"
            onClick={() => commit('noise')}
            disabled={atEnd}
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
              disabled={atEnd}
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
            disabled={atEnd}
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
            <span style={{ width: `${(labeledCount / total) * 100}%` }} />
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
