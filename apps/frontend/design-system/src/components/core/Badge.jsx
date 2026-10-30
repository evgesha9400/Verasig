const CSS = `
.vrs-badge {
  display: inline-flex; align-items: center; gap: 5px;
  height: 22px; padding: 0 9px;
  font-family: var(--font-mono); font-size: var(--text-3xs); font-weight: var(--fw-medium);
  letter-spacing: 0.06em; text-transform: uppercase; line-height: 1;
  border-radius: var(--radius-pill); white-space: nowrap;
  border: 1px solid transparent;
}
.vrs-badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
.vrs-badge__neutral  { background: var(--surface-hover); color: var(--text-muted); }
.vrs-badge__verified { background: var(--verified-bg); color: var(--verified-500); }
.vrs-badge__pending  { background: var(--pending-bg);  color: var(--pending-500); }
.vrs-badge__rejected { background: var(--rejected-bg); color: var(--rejected-500); }
.vrs-badge__info     { background: var(--info-bg);     color: var(--info-500); }
.vrs-badge__outline  { background: transparent; border-color: var(--border-strong); color: var(--text-body); }
.vrs-badge__solid    { background: var(--accent); color: var(--text-on-accent); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-badge-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-badge-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Status badge — small, mono, uppercase. */
export function Badge({
  tone = 'neutral',
  dot = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-badge', `vrs-badge__${tone}`, className].filter(Boolean).join(' ')
  return (
    <span className={cls} {...rest}>
      {dot && <span className="vrs-badge__dot" aria-hidden="true" />}
      {children}
    </span>
  )
}
