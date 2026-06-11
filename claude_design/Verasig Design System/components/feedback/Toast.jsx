import React from 'react';

const CSS = `
.vrs-toast {
  display: flex; align-items: flex-start; gap: 11px;
  width: 340px; padding: 13px 14px;
  background: var(--ink-800); border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  font-family: var(--font-sans);
  animation: vrs-toast-in var(--dur-base) var(--ease-out);
}
@keyframes vrs-toast-in { from { opacity: 0; transform: translateY(8px) scale(0.98); } to { opacity: 1; transform: none; } }
.vrs-toast__dot { flex: none; width: 8px; height: 8px; margin-top: 5px; border-radius: 50%; background: var(--text-muted); }
.vrs-toast__verified .vrs-toast__dot { background: var(--verified-500); box-shadow: 0 0 10px var(--signal-glow); }
.vrs-toast__pending  .vrs-toast__dot { background: var(--pending-500); }
.vrs-toast__rejected .vrs-toast__dot { background: var(--rejected-500); }
.vrs-toast__info     .vrs-toast__dot { background: var(--info-500); }
.vrs-toast__body { flex: 1; min-width: 0; }
.vrs-toast__title { font-size: var(--text-sm); font-weight: var(--fw-semibold); color: var(--text-strong); display: flex; align-items: center; gap: 8px; }
.vrs-toast__time { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); margin-left: auto; }
.vrs-toast__msg { font-size: var(--text-xs); color: var(--text-muted); margin-top: 3px; line-height: 1.45; }
.vrs-toast__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 15px; line-height: 1; padding: 2px; border-radius: var(--radius-xs); }
.vrs-toast__close:hover { color: var(--text-strong); }
.vrs-toast-stack { position: fixed; bottom: 20px; right: 20px; z-index: var(--z-toast); display: flex; flex-direction: column; gap: 10px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-toast-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-toast-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** A single toast notification (presentational). */
export function Toast({ tone = 'info', title, time, onClose, className = '', children, ...rest }) {
  const cls = ['vrs-toast', `vrs-toast__${tone}`, className].filter(Boolean).join(' ');
  return (
    <div className={cls} role="status" {...rest}>
      <span className="vrs-toast__dot" aria-hidden="true" />
      <div className="vrs-toast__body">
        <div className="vrs-toast__title">{title}{time && <span className="vrs-toast__time">{time}</span>}</div>
        {children && <div className="vrs-toast__msg">{children}</div>}
      </div>
      {onClose && <button className="vrs-toast__close" aria-label="Dismiss" onClick={onClose}>×</button>}
    </div>
  );
}

/** Fixed bottom-right container for stacking toasts. */
export function ToastStack({ className = '', children, ...rest }) {
  return <div className={['vrs-toast-stack', className].filter(Boolean).join(' ')} {...rest}>{children}</div>;
}
