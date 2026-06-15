import { InteractiveCard } from '@verasig/design-system'

/* Shared provider card used by Sources (Telegram) and Exchanges (Bybit). Owns
   the `.vrs-src-card` shell: a logo + name/kind title row with an optional
   status badge, a description, and a foot row of meta + action. Pass `onClick`
   to make it a keyboard-accessible button, `empty` for the placeholder variant,
   or `children` to replace the desc/foot body (e.g. an inline config form). */
export function SourceCard({
  logo = null,
  name,
  kind,
  badge = null,
  desc = null,
  meta = null,
  action = null,
  empty = false,
  onClick = null,
  className = '',
  style,
  children
}) {
  const cls = ['vrs-src-card', empty ? 'vrs-src-card--empty' : '', className]
    .filter(Boolean)
    .join(' ')

  if (empty) {
    return (
      <div className={cls} style={style}>
        <div className="vrs-src-card__desc" style={{ flex: 'none' }}>
          {desc}
        </div>
      </div>
    )
  }

  const body = children ?? (
    <>
      {desc && <div className="vrs-src-card__desc">{desc}</div>}
      {(meta || action) && (
        <div className="vrs-src-card__foot">
          <span className="vrs-src-meta">{meta}</span>
          {action}
        </div>
      )}
    </>
  )

  const content = (
    <>
      <div className="vrs-src-card__top">
        {logo}
        <div style={{ flex: 1 }}>
          <div className="vrs-src-card__name">{name}</div>
          <div className="vrs-src-card__kind">{kind}</div>
        </div>
        {badge}
      </div>
      {body}
    </>
  )

  if (onClick) {
    return (
      <InteractiveCard className={cls} onClick={onClick}>
        {content}
      </InteractiveCard>
    )
  }
  return (
    <div className={cls} style={style}>
      {content}
    </div>
  )
}
