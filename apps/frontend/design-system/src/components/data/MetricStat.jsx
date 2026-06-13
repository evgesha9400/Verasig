const CSS = `
.vrs-stat { display: flex; flex-direction: column; gap: 6px; }
.vrs-stat__label { font-family: var(--font-mono); font-size: var(--text-3xs); letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); }
.vrs-stat__value { font-family: var(--font-mono); font-feature-settings: "tnum" 1; font-size: var(--text-3xl); font-weight: var(--fw-medium); color: var(--text-strong); line-height: 1; letter-spacing: -0.01em; display: flex; align-items: baseline; gap: 4px; }
.vrs-stat__unit { font-size: var(--text-lg); color: var(--text-muted); font-weight: var(--fw-regular); }
.vrs-stat__row { display: flex; align-items: center; gap: 10px; }
.vrs-stat__delta { display: inline-flex; align-items: center; gap: 3px; font-family: var(--font-mono); font-size: var(--text-2xs); font-weight: var(--fw-medium); }
.vrs-stat__delta.up { color: var(--verified-500); }
.vrs-stat__delta.down { color: var(--rejected-500); }
.vrs-stat__delta.flat { color: var(--text-muted); }
.vrs-stat__caption { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-faint); }
.vrs-stat__sm .vrs-stat__value { font-size: var(--text-xl); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-stat-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-stat-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

const ARROW = {
  up: <path d="M7 17 17 7M17 7H9M17 7v8" />,
  down: <path d="M7 7l10 10M17 17H9M17 17V9" />,
  flat: <path d="M5 12h14" />
}

/** Big metric value with label, unit, delta and caption. */
export function MetricStat({
  label,
  value,
  unit,
  delta,
  trend = 'flat',
  caption,
  size = 'md',
  className = '',
  ...rest
}) {
  const cls = ['vrs-stat', size === 'sm' ? 'vrs-stat__sm' : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={cls} {...rest}>
      {label && <div className="vrs-stat__label">{label}</div>}
      <div className="vrs-stat__row">
        <div className="vrs-stat__value">
          {value}
          {unit && <span className="vrs-stat__unit">{unit}</span>}
        </div>
        {delta != null && (
          <span className={`vrs-stat__delta ${trend}`}>
            <svg
              viewBox="0 0 24 24"
              width="13"
              height="13"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {ARROW[trend]}
            </svg>
            {delta}
          </span>
        )}
      </div>
      {caption && <div className="vrs-stat__caption">{caption}</div>}
    </div>
  )
}
