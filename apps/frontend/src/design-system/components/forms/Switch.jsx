import React from 'react';

const CSS = `
.vrs-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
.vrs-switch.is-disabled { opacity: 0.5; cursor: not-allowed; }
.vrs-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.vrs-switch__track {
  position: relative; flex: none; width: 38px; height: 22px;
  background: var(--surface-hover); border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill);
  transition: background var(--dur-base) var(--ease-out), border-color var(--dur-base) var(--ease-out);
}
.vrs-switch__thumb {
  position: absolute; top: 2px; left: 2px; width: 16px; height: 16px;
  background: var(--text-muted); border-radius: 50%;
  transition: transform var(--dur-base) var(--ease-snap), background var(--dur-base) var(--ease-out);
}
.vrs-switch input:checked + .vrs-switch__track { background: var(--accent); border-color: var(--accent); }
.vrs-switch input:checked + .vrs-switch__track .vrs-switch__thumb { transform: translateX(16px); background: var(--text-on-accent); }
.vrs-switch input:focus-visible + .vrs-switch__track { box-shadow: var(--focus-ring); }
.vrs-switch__label { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-switch-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-switch-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Toggle switch. */
export function Switch({ label, disabled = false, className = '', id, ...rest }) {
  const cls = ['vrs-switch', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return (
    <label className={cls}>
      <input type="checkbox" role="switch" disabled={disabled} id={id} {...rest} />
      <span className="vrs-switch__track"><span className="vrs-switch__thumb" /></span>
      {label && <span className="vrs-switch__label">{label}</span>}
    </label>
  );
}
