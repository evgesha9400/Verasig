const CSS = `
.vrs-pop {
  position: relative;
  display: inline-flex;
}
.vrs-pop__trigger {
  display: inline-flex;
}
.vrs-pop__trigger:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-sm);
}
.vrs-pop__panel {
  position: absolute;
  z-index: var(--z-tooltip);
  top: calc(100% + 8px);
  left: 0;
  width: 290px;
  display: flex;
  flex-direction: column;
  padding: 12px 13px 13px;
  background: var(--surface-overlay);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
}
.vrs-pop__panel::before {
  content: '';
  position: absolute;
}
/* Bridge sits on the edge facing the trigger so the cursor can cross the gap. */
.vrs-pop__panel[data-side='bottom']::before {
  top: -10px;
  left: 0;
  right: 0;
  height: 10px;
}
.vrs-pop__panel[data-side='top']::before {
  bottom: -10px;
  left: 0;
  right: 0;
  height: 10px;
}
.vrs-pop__panel[data-side='left']::before {
  right: -10px;
  top: 0;
  bottom: 0;
  width: 10px;
}
.vrs-pop__panel[data-side='right']::before {
  left: -10px;
  top: 0;
  bottom: 0;
  width: 10px;
}
.vrs-pop__panel[data-side='top'] {
  top: auto;
  bottom: calc(100% + 8px);
  transform: translateY(-4px);
}
.vrs-pop__panel[data-align='end'] {
  left: auto;
  right: 0;
}
.vrs-pop:hover .vrs-pop__panel,
.vrs-pop:focus-within .vrs-pop__panel {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-pop-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-pop-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

export function Popover({
  trigger,
  side = 'bottom',
  align = 'start',
  role = 'tooltip',
  className = '',
  panelClassName = '',
  children,
  ...rest
}) {
  return (
    <span className={['vrs-pop', className].filter(Boolean).join(' ')} {...rest}>
      <span className="vrs-pop__trigger" tabIndex={0}>
        {trigger}
      </span>
      <span
        className={['vrs-pop__panel', panelClassName].filter(Boolean).join(' ')}
        role={role}
        data-side={side}
        data-align={align}
      >
        {children}
      </span>
    </span>
  )
}
