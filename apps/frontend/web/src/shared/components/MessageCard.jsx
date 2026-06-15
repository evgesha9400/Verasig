import { Icon } from '@verasig/design-system'

/* Shared signal-message card used by the Label and Verify swipe decks. Owns the
   card shell, drag transform, swipe stamps and the reply/text/media body; the
   head row differs per step and is supplied via the `head` slot. */

function MessageMedia({ kind }) {
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

export function MessageCard({
  text,
  replyTo = null,
  media = null,
  head = null,
  tone = null,
  isTop = false,
  dragX = 0,
  style,
  stampPositive = null,
  stampNegative = null
}) {
  const rot = dragX / 22
  const cls = [
    'vrs-card-msg',
    tone === 'signal' ? 'is-signal' : '',
    tone === 'noise' ? 'is-noise' : '',
    isTop ? 'vrs-card-msg--top' : ''
  ]
    .filter(Boolean)
    .join(' ')
  const tStyle = isTop
    ? { transform: `translateX(${dragX}px) rotate(${rot}deg)`, ...style }
    : style

  return (
    <div className={cls} style={tStyle}>
      {isTop && stampPositive && (
        <>
          <span
            className="vrs-card-stamp signal"
            style={{ opacity: Math.max(0, Math.min(1, dragX / 90)) }}
          >
            {stampPositive}
          </span>
          <span
            className="vrs-card-stamp noise"
            style={{ opacity: Math.max(0, Math.min(1, -dragX / 90)) }}
          >
            {stampNegative}
          </span>
        </>
      )}
      <div className="vrs-card-msg__head">{head}</div>
      <div className="vrs-card-msg__body">
        {replyTo && (
          <div className="vrs-card-reply">
            <Icon name="reply" size={12} />
            <span className="vrs-card-reply__body">
              <span className="vrs-card-reply__who">{replyTo.author}</span>
              <span className="vrs-card-reply__txt">{replyTo.text}</span>
            </span>
          </div>
        )}
        <div className="vrs-card-msg__text">{text}</div>
        {media && <MessageMedia kind={media} />}
      </div>
    </div>
  )
}
