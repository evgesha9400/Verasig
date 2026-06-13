const CSS = `
.vrs-card {
  background: var(--surface-card); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); overflow: hidden;
  color: inherit;
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out), transform var(--dur-instant) var(--ease-out);
}
.vrs-card:is(button, a) { appearance: none; font: inherit; text-align: left; text-decoration: none; width: 100%; }
.vrs-card:is(button) { cursor: default; }
.vrs-card__pad { padding: var(--space-5); }
.vrs-card__interactive { cursor: pointer; }
.vrs-card__interactive:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); }
.vrs-card__interactive:active { transform: translateY(1px); }
.vrs-card__interactive:focus-visible { outline: none; box-shadow: var(--focus-ring), var(--shadow-md); }
.vrs-card__selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent), var(--glow-soft); }
.vrs-card__overlay { background: var(--surface-overlay); box-shadow: var(--shadow-pop); }
.vrs-card__glow { border-color: transparent; box-shadow: var(--glow-signal); }
.vrs-card__head { display: flex; align-items: center; gap: 12px; padding: 14px var(--space-5); border-bottom: 1px solid var(--border-subtle); }
.vrs-card__title { font-family: var(--font-display); font-size: var(--text-md); font-weight: var(--fw-semibold); color: var(--text-strong); }
.vrs-card__sub { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); margin-top: 1px; }
.vrs-card__head-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.vrs-card__foot { padding: 12px var(--space-5); border-top: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px; }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-card-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-card-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Surface container with optional header / footer. */
export function Card({
  title,
  subtitle,
  headerActions,
  footer,
  padded = true,
  interactive = false,
  glow = false,
  variant = 'static',
  selected = false,
  as = 'div',
  type = 'button',
  className = '',
  children,
  ...rest
}) {
  const Tag = as
  const isInteractive = interactive || variant === 'interactive'
  const isSelected = selected || variant === 'selected'
  const cls = [
    'vrs-card',
    isInteractive ? 'vrs-card__interactive' : '',
    isSelected ? 'vrs-card__selected' : '',
    variant === 'overlay' ? 'vrs-card__overlay' : '',
    glow ? 'vrs-card__glow' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  const hasHead = title || subtitle || headerActions
  return (
    <Tag
      className={cls}
      type={Tag === 'button' ? type : undefined}
      aria-pressed={Tag === 'button' && isSelected ? true : undefined}
      {...rest}
    >
      {hasHead && (
        <div className="vrs-card__head">
          <div>
            {title && <div className="vrs-card__title">{title}</div>}
            {subtitle && <div className="vrs-card__sub">{subtitle}</div>}
          </div>
          {headerActions && (
            <div className="vrs-card__head-actions">{headerActions}</div>
          )}
        </div>
      )}
      <div
        className={padded && !hasHead ? 'vrs-card__pad' : padded ? 'vrs-card__pad' : ''}
      >
        {children}
      </div>
      {footer && <div className="vrs-card__foot">{footer}</div>}
    </Tag>
  )
}
