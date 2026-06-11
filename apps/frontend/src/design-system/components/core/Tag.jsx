import React from 'react';

const CSS = `
.vrs-tag {
  display: inline-flex; align-items: center; gap: 6px;
  height: 26px; padding: 0 10px;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium);
  color: var(--text-body); background: var(--surface-raised);
  border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  line-height: 1; white-space: nowrap;
  transition: border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-tag__sw { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.vrs-tag__rm {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; margin-right: -3px; border-radius: 3px;
  border: 0; background: transparent; color: var(--text-faint); cursor: pointer;
  font-size: 13px; line-height: 1;
}
.vrs-tag__rm:hover { background: var(--surface-hover); color: var(--text-strong); }
.vrs-tag__clickable { cursor: pointer; }
.vrs-tag__clickable:hover { border-color: var(--border-strong); background: var(--surface-hover); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-tag-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-tag-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Interactive tag / chip for filters, channels and providers. */
export function Tag({ swatch, onRemove, onClick, className = '', children, ...rest }) {
  const cls = ['vrs-tag', onClick ? 'vrs-tag__clickable' : '', className].filter(Boolean).join(' ');
  return (
    <span className={cls} onClick={onClick} {...rest}>
      {swatch && <span className="vrs-tag__sw" style={{ background: swatch }} aria-hidden="true" />}
      {children}
      {onRemove && (
        <button className="vrs-tag__rm" aria-label="Remove"
          onClick={(e) => { e.stopPropagation(); onRemove(e); }}>×</button>
      )}
    </span>
  );
}
