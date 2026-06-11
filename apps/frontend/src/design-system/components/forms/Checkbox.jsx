
const CSS = `
.vrs-check { display: inline-flex; align-items: flex-start; gap: 10px; cursor: pointer; user-select: none; }
.vrs-check.is-disabled { opacity: 0.5; cursor: not-allowed; }
.vrs-check input { position: absolute; opacity: 0; width: 0; height: 0; }
.vrs-check__box {
  flex: none; width: 18px; height: 18px; margin-top: 1px;
  border-radius: var(--radius-xs); border: 1.5px solid var(--border-strong);
  background: var(--surface-sunken);
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--text-on-accent);
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.vrs-check:hover .vrs-check__box { border-color: var(--accent); }
.vrs-check input:checked + .vrs-check__box { background: var(--accent); border-color: var(--accent); }
.vrs-check input:focus-visible + .vrs-check__box { box-shadow: var(--focus-ring); }
.vrs-check__box svg { width: 12px; height: 12px; stroke-width: 3; opacity: 0; transform: scale(0.6); transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-snap); }
.vrs-check input:checked + .vrs-check__box svg { opacity: 1; transform: scale(1); }
.vrs-check__text { display: flex; flex-direction: column; gap: 2px; }
.vrs-check__label { font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong); line-height: 1.3; }
.vrs-check__desc { font-family: var(--font-sans); font-size: var(--text-2xs); color: var(--text-muted); }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-check-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-check-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Checkbox with optional label + description. */
export function Checkbox({ label, description, disabled = false, className = '', id, ...rest }) {
  const cls = ['vrs-check', disabled ? 'is-disabled' : '', className].filter(Boolean).join(' ');
  return (
    <label className={cls}>
      <input type="checkbox" disabled={disabled} id={id} {...rest} />
      <span className="vrs-check__box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
      </span>
      {(label || description) && (
        <span className="vrs-check__text">
          {label && <span className="vrs-check__label">{label}</span>}
          {description && <span className="vrs-check__desc">{description}</span>}
        </span>
      )}
    </label>
  );
}
