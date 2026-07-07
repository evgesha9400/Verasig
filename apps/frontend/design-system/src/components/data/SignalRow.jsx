import { StatusPill } from './StatusPill.jsx'
import { ConfidenceBar } from './ConfidenceBar.jsx'

const CSS = `
.vrs-srow {
  display: grid;
  grid-template-columns: 22px minmax(150px, 1.4fr) minmax(120px, 1fr) 130px auto;
  align-items: center; gap: 16px;
  padding: 12px 16px; background: var(--surface-card);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-srow.is-interactive { cursor: pointer; }
.vrs-srow.is-interactive:hover { border-color: var(--border-strong); background: var(--surface-raised); }
.vrs-srow__rail { width: 3px; height: 26px; border-radius: 3px; background: var(--text-faint); }
.vrs-srow.s-verified .vrs-srow__rail { background: var(--verified-500); }
.vrs-srow.s-pending  .vrs-srow__rail { background: var(--pending-500); }
.vrs-srow.s-rejected .vrs-srow__rail { background: var(--rejected-500); }
.vrs-srow.s-observing .vrs-srow__rail { background: var(--info-500); }
.vrs-srow__main { min-width: 0; }
.vrs-srow__sym { font-family: var(--font-mono); font-size: var(--text-sm); font-weight: var(--fw-medium); color: var(--text-strong); }
.vrs-srow__id  { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); margin-top: 2px; }
.vrs-srow__src { display: flex; align-items: center; gap: 7px; min-width: 0; }
.vrs-srow__srcname { font-family: var(--font-sans); font-size: var(--text-xs); color: var(--text-body); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vrs-srow__ch { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-muted); }
.vrs-srow__right { display: flex; align-items: center; gap: 14px; justify-content: flex-end; }
.vrs-srow__time { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); white-space: nowrap; }
.vrs-srow__avatar { width: 22px; height: 22px; border-radius: var(--radius-sm); flex: none; display: inline-flex; align-items: center; justify-content: center; font-family: var(--font-mono); font-size: 9px; font-weight: 600; color: var(--text-on-accent); text-transform: uppercase; }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-srow-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-srow-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** A single signal row — symbol, source, channel, confidence, status, time. */
export function SignalRow({
  symbol,
  signalId,
  provider,
  providerTint = 'var(--viz-2)',
  channel,
  confidence,
  threshold = 80,
  status = 'pending',
  time,
  onClick,
  className = '',
  ...rest
}) {
  const initials = (provider || '').slice(0, 2)
  const interactive = Boolean(onClick)
  const cls = ['vrs-srow', `s-${status}`, interactive ? 'is-interactive' : '', className]
    .filter(Boolean)
    .join(' ')
  function onKeyDown(event) {
    rest.onKeyDown && rest.onKeyDown(event)
    if (event.defaultPrevented) return
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onClick(event)
  }
  return (
    <div
      className={cls}
      {...rest}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={interactive ? onKeyDown : undefined}
    >
      <span className="vrs-srow__rail" aria-hidden="true" />
      <div className="vrs-srow__main">
        <div className="vrs-srow__sym">{symbol}</div>
        {signalId && <div className="vrs-srow__id">{signalId}</div>}
      </div>
      <div className="vrs-srow__src">
        <span className="vrs-srow__avatar" style={{ background: providerTint }}>
          {initials}
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="vrs-srow__srcname">{provider}</div>
          {channel && <div className="vrs-srow__ch">{channel}</div>}
        </div>
      </div>
      <div>
        {confidence != null && (
          <ConfidenceBar value={confidence} threshold={threshold} label={null} />
        )}
      </div>
      <div className="vrs-srow__right">
        <StatusPill status={status} pulse={status === 'pending'} />
        {time && <span className="vrs-srow__time">{time}</span>}
      </div>
    </div>
  )
}
