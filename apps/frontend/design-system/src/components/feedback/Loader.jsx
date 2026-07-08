/* Inject component styles once (self-contained, token-driven).

   One heartbeat family for every page/section loader:
   - variant="bar"  → an accent gradient band sweeping a thin track (the backfill
     "heartbeat monitor"; canonical for pages/sections).
   - variant="dot"  → a pulsing accent dot for tight inline spots.
   Both share the accent color (--signal-500 / --accent) and the easing tokens.
   Buttons keep their own rotating ring — a bar can't sit inside a label. */
const CSS = `
.vrs-loader {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 10px; font-family: var(--font-sans);
}
.vrs-loader--sm { min-height: 120px; }
.vrs-loader--lg { min-height: 380px; }

/* ---- bar: the sweep band ---- */
.vrs-loader-bar {
  display: block; height: 3px; border-radius: 2px;
  background: var(--surface-raised); overflow: hidden; position: relative;
}
.vrs-loader-bar--sm { width: 180px; }
.vrs-loader-bar--md { width: 300px; }
.vrs-loader-bar--lg { width: 420px; max-width: 90vw; }
.vrs-loader-bar::after {
  content: ''; position: absolute; top: 0; left: 0; height: 100%; width: 38%;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--signal-500), transparent);
  animation: vrs-loader-sweep 1.5s var(--ease-in-out) infinite;
}

/* ---- dot: the pulse ---- */
.vrs-loader-dot {
  display: block; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 0 0 var(--signal-glow);
  animation: vrs-loader-pulse 1.2s var(--ease-out) infinite;
}
.vrs-loader-dot--sm { width: 8px; height: 8px; }
.vrs-loader-dot--md { width: 10px; height: 10px; }
.vrs-loader-dot--lg { width: 12px; height: 12px; }

@keyframes vrs-loader-sweep { 0% { left: -40%; } 100% { left: 100%; } }
@keyframes vrs-loader-pulse {
  0% { box-shadow: 0 0 0 0 var(--signal-glow); }
  70% { box-shadow: 0 0 0 7px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

/* Calm the heartbeat for readers who ask for less motion. */
@media (prefers-reduced-motion: reduce) {
  .vrs-loader-bar::after, .vrs-loader-dot { animation-duration: 3s; }
}
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-loader-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-loader-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/**
 * Verasig loading heartbeat. Renders a centered block (glyph + title + note)
 * when given `title`/`note`, or a bare glyph for inline use when given neither.
 */
export function Loader({
  variant = 'bar',
  size = 'md',
  title,
  note,
  className = '',
  ...rest
}) {
  const glyphClass =
    variant === 'dot'
      ? `vrs-loader-dot vrs-loader-dot--${size}`
      : `vrs-loader-bar vrs-loader-bar--${size}`

  // Bare glyph: no wrapper text, so the glyph itself carries the live region.
  if (!title && !note) {
    const cls = [glyphClass, className].filter(Boolean).join(' ')
    return <span className={cls} role="status" aria-live="polite" {...rest} />
  }

  const cls = ['vrs-loader', size !== 'md' ? `vrs-loader--${size}` : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={cls} role="status" aria-live="polite" {...rest}>
      <span className={glyphClass} aria-hidden="true" />
      {title && <div className="vrs-empty__title">{title}</div>}
      {note && <div className="vrs-empty__note">{note}</div>}
    </div>
  )
}
