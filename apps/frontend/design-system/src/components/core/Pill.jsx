/* Small inline pill / chip — the compact, mono, pill-shaped label the product
   kept hand-rolling (recommended / soon tags, profit-loss indicators). Distinct
   from Badge, which is the taller 22px status badge. Compose with:
   - tone:    accent | pending | profit | loss | neutral  (color + fill)
   - variant: soft (filled)  | outline (bordered, no fill)
   - size:    sm (default)   | xs
   - numeric: tabular, non-uppercase, semibold — for +/- values with an icon */
const CSS = `
.vrs-pill {
  display: inline-flex; align-items: center;
  font-family: var(--font-mono); font-size: var(--text-3xs);
  letter-spacing: 0.1em; text-transform: uppercase; line-height: 1;
  border-radius: var(--radius-pill); white-space: nowrap;
}
.vrs-pill svg { flex: none; }
.vrs-pill__xs { font-size: 9px; letter-spacing: 0.12em; }
.vrs-pill__num {
  text-transform: none; letter-spacing: 0.01em; gap: 2px;
  font-weight: var(--fw-semibold); font-variant-numeric: tabular-nums;
}
.vrs-pill__soft { padding: 2px 7px; }
.vrs-pill__num.vrs-pill__soft { padding: 2px 7px 2px 4px; }
.vrs-pill__outline { padding: 2px 8px; border: 1px solid transparent; }

.vrs-pill__neutral { color: var(--text-muted); }
.vrs-pill__neutral.vrs-pill__soft { background: var(--surface-hover); }
.vrs-pill__neutral.vrs-pill__outline { border-color: var(--border-strong); }
.vrs-pill__accent { color: var(--accent-text); }
.vrs-pill__accent.vrs-pill__soft { background: var(--accent-quiet); }
.vrs-pill__accent.vrs-pill__outline { border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.vrs-pill__pending { color: var(--pending-500); }
.vrs-pill__pending.vrs-pill__soft { background: var(--pending-bg); }
.vrs-pill__pending.vrs-pill__outline { border-color: color-mix(in srgb, var(--pending-500) 40%, transparent); }
.vrs-pill__profit { color: var(--verified-500); }
.vrs-pill__profit.vrs-pill__soft { background: color-mix(in srgb, var(--verified-500) 14%, transparent); }
.vrs-pill__loss { color: var(--rejected-500); }
.vrs-pill__loss.vrs-pill__soft { background: color-mix(in srgb, var(--rejected-500) 14%, transparent); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-pill-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-pill-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Compact inline pill / chip. */
export function Pill({
  tone = 'neutral',
  variant = 'soft',
  size = 'sm',
  numeric = false,
  className = '',
  children,
  ...rest
}) {
  const cls = [
    'vrs-pill',
    `vrs-pill__${tone}`,
    `vrs-pill__${variant}`,
    size === 'xs' ? 'vrs-pill__xs' : '',
    numeric ? 'vrs-pill__num' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  )
}
