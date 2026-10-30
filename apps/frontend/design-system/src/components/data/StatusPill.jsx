const CSS = `
.vrs-status {
  display: inline-flex; align-items: center; gap: 7px;
  height: 26px; padding: 0 11px 0 9px;
  border-radius: var(--radius-pill); border: 1px solid transparent;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); line-height: 1;
}
.vrs-status__ic { display: inline-flex; }
.vrs-status__ic svg { width: 14px; height: 14px; display: block; }
.vrs-status__verified { background: var(--verified-bg); color: var(--verified-500); border-color: color-mix(in srgb, var(--verified-500) 28%, transparent); }
.vrs-status__pending  { background: var(--pending-bg);  color: var(--pending-500);  border-color: color-mix(in srgb, var(--pending-500) 28%, transparent); }
.vrs-status__rejected { background: var(--rejected-bg); color: var(--rejected-500); border-color: color-mix(in srgb, var(--rejected-500) 28%, transparent); }
.vrs-status__observing{ background: var(--info-bg);     color: var(--info-500);     border-color: color-mix(in srgb, var(--info-500) 28%, transparent); }
.vrs-status__pulse { position: relative; }
.vrs-status__pulse .vrs-status__ic::after {
  content: ''; position: absolute; left: 9px; top: 50%; width: 14px; height: 14px;
  transform: translateY(-50%); border-radius: 50%;
  box-shadow: 0 0 0 0 currentColor; opacity: 0.5;
  animation: vrs-status-pulse 1.8s var(--ease-out) infinite;
}
@keyframes vrs-status-pulse { 70%,100% { box-shadow: 0 0 0 7px transparent; opacity: 0; } }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-status-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-status-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

const GLYPH = {
  verified: <path d="M20 6 9 17l-5-5" />,
  pending: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  rejected: <path d="M18 6 6 18M6 6l12 12" />,
  observing: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
    </>
  )
}
const LABELS = {
  verified: 'Verified',
  pending: 'Pending',
  rejected: 'Rejected',
  observing: 'Observing'
}

/** Verification status pill with icon. */
export function StatusPill({
  status = 'pending',
  label,
  pulse = false,
  className = '',
  ...rest
}) {
  const cls = [
    'vrs-status',
    `vrs-status__${status}`,
    pulse ? 'vrs-status__pulse' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <span className={cls} {...rest}>
      <span className="vrs-status__ic">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {GLYPH[status]}
        </svg>
      </span>
      {label || LABELS[status]}
    </span>
  )
}
