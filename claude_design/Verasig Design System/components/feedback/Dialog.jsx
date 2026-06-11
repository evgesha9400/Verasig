import React from 'react';

const CSS = `
.vrs-dialog__scrim {
  position: fixed; inset: 0; z-index: var(--z-modal);
  background: rgba(6,7,9,0.66); backdrop-filter: blur(var(--blur-sm));
  display: flex; align-items: center; justify-content: center; padding: 24px;
  animation: vrs-dialog-fade var(--dur-base) var(--ease-out);
}
@keyframes vrs-dialog-fade { from { opacity: 0; } to { opacity: 1; } }
.vrs-dialog {
  width: 100%; max-width: 460px;
  background: var(--surface-card); border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl); box-shadow: var(--shadow-pop);
  animation: vrs-dialog-rise var(--dur-base) var(--ease-out);
}
@keyframes vrs-dialog-rise { from { opacity: 0; transform: translateY(10px) scale(0.99); } to { opacity: 1; transform: none; } }
.vrs-dialog__head { display: flex; align-items: flex-start; gap: 14px; padding: 20px 20px 0; }
.vrs-dialog__icon { flex: none; width: 38px; height: 38px; border-radius: var(--radius-md); display: inline-flex; align-items: center; justify-content: center; background: var(--accent-quiet); color: var(--accent-text); }
.vrs-dialog__icon svg { width: 19px; height: 19px; }
.vrs-dialog__titles { flex: 1; min-width: 0; }
.vrs-dialog__title { font-family: var(--font-display); font-size: var(--text-lg); font-weight: var(--fw-semibold); color: var(--text-strong); }
.vrs-dialog__desc { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-muted); margin-top: 4px; line-height: 1.5; }
.vrs-dialog__close { flex: none; border: 0; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 19px; line-height: 1; padding: 4px; border-radius: var(--radius-xs); }
.vrs-dialog__close:hover { color: var(--text-strong); background: var(--surface-hover); }
.vrs-dialog__body { padding: 16px 20px; font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-body); line-height: 1.55; }
.vrs-dialog__foot { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px 20px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-dialog-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-dialog-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Modal dialog. Render conditionally on `open`. */
export function Dialog({ open, title, description, icon, onClose, footer, className = '', children }) {
  if (!open) return null;
  return (
    <div className="vrs-dialog__scrim" onClick={onClose}>
      <div className={['vrs-dialog', className].filter(Boolean).join(' ')} role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="vrs-dialog__head">
          {icon && <span className="vrs-dialog__icon">{icon}</span>}
          <div className="vrs-dialog__titles">
            {title && <div className="vrs-dialog__title">{title}</div>}
            {description && <div className="vrs-dialog__desc">{description}</div>}
          </div>
          {onClose && <button className="vrs-dialog__close" aria-label="Close" onClick={onClose}>×</button>}
        </div>
        {children && <div className="vrs-dialog__body">{children}</div>}
        {footer && <div className="vrs-dialog__foot">{footer}</div>}
      </div>
    </div>
  );
}
