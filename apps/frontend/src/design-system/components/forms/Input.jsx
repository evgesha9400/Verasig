
const CSS = `
.vrs-field { display: flex; flex-direction: column; gap: 6px; }
.vrs-field__label { font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-body); display: flex; gap: 6px; align-items: center; }
.vrs-field__req { color: var(--accent-text); }
.vrs-field__hint { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
.vrs-field__hint.is-error { color: var(--rejected-500); }

.vrs-input {
  display: flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 12px;
  background: var(--surface-sunken); color: var(--text-strong);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.vrs-input:hover { border-color: var(--border-strong); }
.vrs-input:focus-within { border-color: var(--border-focus); box-shadow: 0 0 0 3px var(--accent-quiet); background: var(--surface-card); }
.vrs-input input {
  flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
  font-family: var(--font-sans); font-size: var(--text-sm); color: inherit;
}
/* The wrapper owns the focus affordance (border + ring) via :focus-within above.
   Neutralize the inner control's own ring so the global :focus-visible catch-all
   in base.css can't paint a second, concentric ring inside the wrapper. */
.vrs-input input:focus,
.vrs-input input:focus-visible {
  outline: none;
  box-shadow: none;
}
.vrs-input input::placeholder { color: var(--text-faint); }
.vrs-input__icon { color: var(--text-muted); display: inline-flex; flex: none; }
.vrs-input__icon svg { width: 16px; height: 16px; display:block; }
.vrs-input.is-error { border-color: var(--rejected-500); }
.vrs-input.is-error:focus-within { box-shadow: 0 0 0 3px var(--rejected-bg); }
.vrs-input.is-mono input { font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.01em; }
.vrs-input.is-disabled { opacity: 0.5; pointer-events: none; }
.vrs-input__kbd { font-family: var(--font-mono); font-size: var(--text-3xs); color: var(--text-faint); border: 1px solid var(--border-default); border-radius: var(--radius-xs); padding: 1px 5px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-input-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-input-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Text input with optional label, icon, hint and error state. */
export function Input({
  label, hint, error, required = false,
  iconLeft, trailing, mono = false, disabled = false,
  id, className = '', ...rest
}) {
  const fieldId = id || (label ? `vrs-${label.replace(/\s+/g, '-').toLowerCase()}` : undefined);
  const boxCls = ['vrs-input', error ? 'is-error' : '', mono ? 'is-mono' : '', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return (
    <div className="vrs-field">
      {label && (
        <label className="vrs-field__label" htmlFor={fieldId}>
          {label}{required && <span className="vrs-field__req">*</span>}
        </label>
      )}
      <div className={boxCls}>
        {iconLeft && <span className="vrs-input__icon">{iconLeft}</span>}
        <input id={fieldId} disabled={disabled} {...rest} />
        {trailing}
      </div>
      {(error || hint) && <span className={`vrs-field__hint ${error ? 'is-error' : ''}`}>{error || hint}</span>}
    </div>
  );
}
