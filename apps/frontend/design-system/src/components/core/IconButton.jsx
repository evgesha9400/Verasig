const CSS = `
.vrs-iconbtn {
  --_s: 38px;
  display: inline-flex; align-items: center; justify-content: center;
  width: var(--_s); height: var(--_s); padding: 0; flex: none;
  border-radius: 7px; border: 1px solid transparent;
  background: transparent; color: var(--text-muted); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out),
              background-image var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-iconbtn svg { width: 18px; height: 18px; display: block; }
.vrs-iconbtn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-strong); }
.vrs-iconbtn:active:not(:disabled) { background: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.25); }
.vrs-iconbtn:disabled { opacity: 0.4; cursor: not-allowed; }
.vrs-iconbtn__sz-sm { --_s: 30px; }
.vrs-iconbtn__sz-sm svg { width: 15px; height: 15px; }
.vrs-iconbtn__sz-lg { --_s: 46px; }
.vrs-iconbtn__sz-lg svg { width: 20px; height: 20px; }
.vrs-iconbtn__solid {
  color: var(--text-body); border-color: var(--border-strong);
  background-color: var(--surface-raised);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-raised) 90%, #fff), color-mix(in srgb, var(--surface-raised) 94%, #000));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 1.5px rgba(0,0,0,0.3);
}
.vrs-iconbtn__solid:hover:not(:disabled) { color: var(--text-strong); border-color: color-mix(in srgb, var(--accent) 48%, var(--border-strong)); background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-hover) 90%, #fff), var(--surface-hover)); }
.vrs-iconbtn__solid:active:not(:disabled) { background-image: none; background-color: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }
.vrs-iconbtn__accent { background: var(--accent-quiet); color: var(--accent-text); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 22%, transparent); }
.vrs-iconbtn__accent:hover:not(:disabled) { color: var(--accent-text); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 22%, transparent), 0 0 14px var(--signal-glow); }
.vrs-iconbtn__accent:active:not(:disabled) { background-color: var(--accent-quiet); }
/* Focus ring last, and as specific as every variant :hover/:active box-shadow
   above, so a keyboard-focused icon button never loses its ring. */
.vrs-iconbtn:focus-visible,
.vrs-iconbtn:focus-visible:hover:not(:disabled),
.vrs-iconbtn:focus-visible:active:not(:disabled) {
  outline: none; box-shadow: var(--focus-ring), 0 0 18px var(--signal-glow);
}
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-iconbtn-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-iconbtn-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Square icon-only button. */
export function IconButton({
  variant = 'ghost',
  size = 'md',
  label,
  type = 'button',
  className = '',
  children,
  ...rest
}) {
  const cls = [
    'vrs-iconbtn',
    variant !== 'ghost' ? `vrs-iconbtn__${variant}` : '',
    size !== 'md' ? `vrs-iconbtn__sz-${size}` : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <button className={cls} type={type} aria-label={label} title={label} {...rest}>
      {children}
    </button>
  )
}
