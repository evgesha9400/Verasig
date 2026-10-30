const CSS = `
.vrs-conf { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.vrs-conf__top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.vrs-conf__label { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
.vrs-conf__val { font-family: var(--font-mono); font-feature-settings: "tnum" 1; font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-strong); }
.vrs-conf__track { position: relative; height: 6px; border-radius: var(--radius-pill); background: var(--surface-hover); overflow: hidden; }
.vrs-conf__fill { position: absolute; inset: 0 auto 0 0; border-radius: var(--radius-pill); transition: width var(--dur-slow) var(--ease-out); }
.vrs-conf__threshold { position: absolute; top: -2px; bottom: -2px; width: 2px; background: var(--text-faint); border-radius: 2px; }
.vrs-conf__seg { display: flex; gap: 3px; }
.vrs-conf__tick { flex: 1; height: 6px; border-radius: 2px; background: var(--surface-hover); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-conf-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-conf-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

function colorFor(value, threshold) {
  if (value < threshold) return 'var(--rejected-500)'
  // clamp the pending band to 100 so a top score with a high threshold still
  // reaches "verified" instead of being stuck pending (threshold + 8 > 100).
  if (value < Math.min(100, threshold + 8)) return 'var(--pending-500)'
  return 'var(--verified-500)'
}

/** Confidence meter — a bar (or segmented) showing a 0–100 score vs a quorum threshold. */
export function ConfidenceBar({
  value = 0,
  threshold = 80,
  label = 'Confidence',
  showValue = true,
  segments = 0,
  className = '',
  ...rest
}) {
  const v = Math.max(0, Math.min(100, value))
  const color = colorFor(v, threshold)
  return (
    <div className={['vrs-conf', className].filter(Boolean).join(' ')} {...rest}>
      {(label || showValue) && (
        <div className="vrs-conf__top">
          {label && <span className="vrs-conf__label">{label}</span>}
          {showValue && <span className="vrs-conf__val">{v.toFixed(1)}%</span>}
        </div>
      )}
      {segments > 0 ? (
        <div className="vrs-conf__seg">
          {Array.from({ length: segments }).map((_, i) => (
            <span
              key={i}
              className="vrs-conf__tick"
              style={{
                background: i < Math.round((v / 100) * segments) ? color : undefined
              }}
            />
          ))}
        </div>
      ) : (
        <div className="vrs-conf__track">
          <span
            className="vrs-conf__fill"
            style={{ width: `${v}%`, background: color }}
          />
          {threshold > 0 && threshold < 100 && (
            <span
              className="vrs-conf__threshold"
              style={{ left: `${threshold}%` }}
              title={`Quorum threshold ${threshold}%`}
            />
          )}
        </div>
      )}
    </div>
  )
}
