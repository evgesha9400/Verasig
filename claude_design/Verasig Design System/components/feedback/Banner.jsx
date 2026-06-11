import React from 'react';

const CSS = `
.vrs-banner {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: var(--surface-card);
  font-family: var(--font-sans);
}
.vrs-banner__accent { width: 3px; border-radius: 3px; align-self: stretch; flex: none; background: var(--text-muted); }
.vrs-banner__icon { flex: none; margin-top: 1px; color: var(--text-muted); }
.vrs-banner__icon svg { width: 18px; height: 18px; display: block; }
.vrs-banner__body { flex: 1; min-width: 0; }
.vrs-banner__title { font-size: var(--text-sm); font-weight: var(--fw-semibold); color: var(--text-strong); margin-bottom: 2px; }
.vrs-banner__msg { font-size: var(--text-xs); color: var(--text-body); line-height: 1.5; }
.vrs-banner__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px; border-radius: var(--radius-xs); }
.vrs-banner__close:hover { color: var(--text-strong); background: var(--surface-hover); }
.vrs-banner__actions { display: flex; gap: 8px; margin-top: 10px; }

.vrs-banner__verified .vrs-banner__accent, .vrs-banner__verified .vrs-banner__icon { background: var(--verified-500); color: var(--verified-500); }
.vrs-banner__pending  .vrs-banner__accent, .vrs-banner__pending .vrs-banner__icon  { background: var(--pending-500);  color: var(--pending-500); }
.vrs-banner__rejected .vrs-banner__accent, .vrs-banner__rejected .vrs-banner__icon { background: var(--rejected-500); color: var(--rejected-500); }
.vrs-banner__info     .vrs-banner__accent, .vrs-banner__info .vrs-banner__icon     { background: var(--info-500);     color: var(--info-500); }
.vrs-banner__verified .vrs-banner__icon, .vrs-banner__pending .vrs-banner__icon, .vrs-banner__rejected .vrs-banner__icon, .vrs-banner__info .vrs-banner__icon { background: transparent; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-banner-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-banner-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

const ICONS = {
  verified: <path d="M20 6 9 17l-5-5"/>,
  pending: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  rejected: <><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></>,
  neutral: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></>,
};

/** Inline banner / alert with semantic tone. */
export function Banner({ tone = 'info', title, icon, onClose, actions, className = '', children, ...rest }) {
  const cls = ['vrs-banner', `vrs-banner__${tone}`, className].filter(Boolean).join(' ');
  return (
    <div className={cls} role="status" {...rest}>
      <span className="vrs-banner__accent" aria-hidden="true" />
      <span className="vrs-banner__icon">
        {icon || <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{ICONS[tone] || ICONS.info}</svg>}
      </span>
      <div className="vrs-banner__body">
        {title && <div className="vrs-banner__title">{title}</div>}
        {children && <div className="vrs-banner__msg">{children}</div>}
        {actions && <div className="vrs-banner__actions">{actions}</div>}
      </div>
      {onClose && <button className="vrs-banner__close" aria-label="Dismiss" onClick={onClose}>×</button>}
    </div>
  );
}
