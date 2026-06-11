
const CSS = `
.vrs-tip { position: relative; display: inline-flex; }
.vrs-tip__pop {
  position: absolute; z-index: var(--z-tooltip);
  bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%) translateY(4px);
  background: var(--ink-800); color: var(--text-strong);
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  padding: 6px 9px; font-family: var(--font-sans); font-size: var(--text-2xs); line-height: 1.4;
  white-space: nowrap; box-shadow: var(--shadow-md);
  opacity: 0; pointer-events: none;
  transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);
}
.vrs-tip__pop[data-side="bottom"] { bottom: auto; top: calc(100% + 8px); transform: translateX(-50%) translateY(-4px); }
.vrs-tip:hover .vrs-tip__pop, .vrs-tip:focus-within .vrs-tip__pop { opacity: 1; transform: translateX(-50%) translateY(0); }
.vrs-tip__pop kbd { font-family: var(--font-mono); color: var(--text-muted); margin-left: 6px; }
`;
if (typeof document !== 'undefined' && !document.getElementById('vrs-tip-css')) {
  const s = document.createElement('style');
  s.id = 'vrs-tip-css';
  s.textContent = CSS;
  document.head.appendChild(s);
}

/** Hover/focus tooltip wrapping its single child. */
export function Tooltip({ label, side = 'top', shortcut, className = '', children, ...rest }) {
  return (
    <span className={['vrs-tip', className].filter(Boolean).join(' ')} {...rest}>
      {children}
      <span className="vrs-tip__pop" role="tooltip" data-side={side}>
        {label}{shortcut && <kbd>{shortcut}</kbd>}
      </span>
    </span>
  );
}
