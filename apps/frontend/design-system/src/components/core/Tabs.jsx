const CSS = `
.vrs-tabs { display: flex; align-items: center; gap: 2px; position: relative; }
.vrs-tabs__line { border-bottom: 1px solid var(--border-default); }
.vrs-tab {
  appearance: none; background: transparent; border: 0; cursor: pointer;
  font-family: var(--font-sans); font-size: var(--text-sm); font-weight: var(--fw-medium);
  color: var(--text-muted); padding: 9px 13px; position: relative;
  display: inline-flex; align-items: center; gap: 7px;
  transition: color var(--dur-fast) var(--ease-out);
}
.vrs-tab:hover { color: var(--text-strong); }
.vrs-tab[aria-selected="true"] { color: var(--text-strong); }
.vrs-tabs__line .vrs-tab { padding-bottom: 11px; }
.vrs-tabs__line .vrs-tab::after {
  content: ''; position: absolute; left: 10px; right: 10px; bottom: -1px; height: 2px;
  background: var(--accent); border-radius: 2px 2px 0 0;
  transform: scaleX(0); transform-origin: center;
  transition: transform var(--dur-base) var(--ease-out);
}
.vrs-tabs__line .vrs-tab[aria-selected="true"]::after { transform: scaleX(1); }
.vrs-tabs__pill { background: var(--surface-sunken); padding: 4px; border-radius: var(--radius-md); gap: 2px; }
.vrs-tabs__pill .vrs-tab { padding: 6px 13px; border-radius: var(--radius-sm); }
.vrs-tabs__pill .vrs-tab[aria-selected="true"] { background: var(--surface-raised); box-shadow: var(--shadow-xs); }
.vrs-tabs__pill .vrs-tab:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.vrs-tab__count {
  font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint);
  background: var(--surface-hover); border-radius: var(--radius-pill); padding: 1px 6px;
}
.vrs-tab[aria-selected="true"] .vrs-tab__count { color: var(--accent-text); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-tabs-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-tabs-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Tab bar — underline or pill style. Controlled via `value`/`onChange`. */
export function Tabs({
  items = [],
  value,
  onChange,
  variant = 'line',
  className = '',
  ...rest
}) {
  const cls = [
    'vrs-tabs',
    variant === 'line' ? 'vrs-tabs__line' : 'vrs-tabs__pill',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={cls} role="tablist" {...rest}>
      {items.map((it) => {
        const id = typeof it === 'string' ? it : it.id
        const label = typeof it === 'string' ? it : it.label
        const count = typeof it === 'string' ? undefined : it.count
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={value === id}
            className="vrs-tab"
            onClick={() => onChange && onChange(id)}
          >
            {label}
            {count != null && <span className="vrs-tab__count">{count}</span>}
          </button>
        )
      })}
    </div>
  )
}
