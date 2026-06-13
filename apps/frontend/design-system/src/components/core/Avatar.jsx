const CSS = `
.vrs-avatar {
  --_s: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); flex: none; position: relative;
  border-radius: var(--radius-pill); overflow: hidden;
  font-family: var(--font-mono); font-size: calc(var(--_s) * 0.36); font-weight: var(--fw-medium);
  color: var(--text-on-accent); background: var(--accent);
  letter-spacing: 0; text-transform: uppercase; user-select: none;
}
.vrs-avatar img { width: 100%; height: 100%; object-fit: cover; }
.vrs-avatar__sz-xs { --_s: 24px; }
.vrs-avatar__sz-sm { --_s: 30px; }
.vrs-avatar__sz-lg { --_s: 48px; }
.vrs-avatar__square { border-radius: var(--radius-md); }
.vrs-avatar__status {
  position: absolute; right: -1px; bottom: -1px;
  width: 30%; height: 30%; min-width: 8px; min-height: 8px;
  border-radius: 50%; border: 2px solid var(--surface-card);
}
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-avatar-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-avatar-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

const TONE = {
  verified: 'var(--verified-500)',
  pending: 'var(--pending-500)',
  rejected: 'var(--rejected-500)',
  offline: 'var(--ink-500)'
}

/** Avatar — image, or initials fallback on a tinted chip. */
export function Avatar({
  src,
  name = '',
  size = 'md',
  square = false,
  status,
  tint,
  className = '',
  ...rest
}) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
  const cls = [
    'vrs-avatar',
    size !== 'md' ? `vrs-avatar__sz-${size}` : '',
    square ? 'vrs-avatar__square' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <span className={cls} style={tint ? { background: tint } : undefined} {...rest}>
      {src ? <img src={src} alt={name} /> : <span>{initials || '—'}</span>}
      {status && (
        <span
          className="vrs-avatar__status"
          style={{ background: TONE[status] || status }}
        />
      )}
    </span>
  )
}
