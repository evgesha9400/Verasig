/* Inject component styles once (self-contained, token-driven). */
const CSS = `
.vrs-btn {
  --_h: 38px; --_px: 15px; --_fs: var(--text-sm);
  position: relative; isolation: isolate;
  display: inline-flex; align-items: center; justify-content: center;
  gap: 8px; height: var(--_h); padding: 0 var(--_px);
  font-family: var(--font-sans); font-size: var(--_fs); font-weight: var(--fw-medium);
  letter-spacing: 0.005em; line-height: 1; white-space: nowrap;
  border-radius: 7px; border: 1px solid transparent;
  cursor: pointer; user-select: none; text-decoration: none;
  transition: background-color var(--dur-fast) var(--ease-out),
              background-image var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out),
              transform var(--dur-instant) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-btn:focus-visible { outline: none; box-shadow: var(--focus-ring), 0 0 18px var(--signal-glow); }
.vrs-btn:disabled:not(.vrs-btn__loading) { opacity: 0.4; cursor: not-allowed; }
.vrs-btn__loading { cursor: progress; }
.vrs-btn__sz-sm { --_h: 30px; --_px: 12px; --_fs: var(--text-xs); }
.vrs-btn__sz-lg { --_h: 46px; --_px: 22px; --_fs: var(--text-md); border-radius: 9px; }

/* icons sit slightly inset & optically aligned */
.vrs-btn svg { width: 1.15em; height: 1.15em; flex: none; }

/* ---- Primary: a machined signal key ---- */
/* No border: the bevel is drawn with inset shadows, which clip to the padding
   box. A 1px transparent border would leave a ring of un-shaded fill OUTSIDE
   the bevel (a pale halo around the edge). Padding compensates so geometry
   matches the bordered variants exactly. */
.vrs-btn__primary {
  border: none; padding: 0 calc(var(--_px) + 1px);
  color: var(--text-on-accent);
  background-color: var(--accent);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--accent) 87%, #fff), var(--accent));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.45), inset 0 -1px 0 rgba(0,0,0,0.10), 0 1px 1.5px rgba(0,0,0,0.4);
}
.vrs-btn__primary:hover:not(:disabled) {
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--accent) 76%, #fff), color-mix(in srgb, var(--accent) 99%, #fff));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 0 16px var(--signal-glow), 0 5px 14px -4px var(--signal-glow);
}
.vrs-btn__primary:active:not(:disabled) {
  background-image: none; background-color: var(--accent-press);
  transform: translateY(1px);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.12);
}

/* ---- Secondary: brushed instrument surface ---- */
.vrs-btn__secondary {
  color: var(--text-strong); border-color: var(--border-strong);
  background-color: var(--surface-raised);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-raised) 90%, #fff), color-mix(in srgb, var(--surface-raised) 94%, #000));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 1.5px rgba(0,0,0,0.3);
}
.vrs-btn__secondary:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--accent) 48%, var(--border-strong));
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-hover) 90%, #fff), var(--surface-hover));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 0 12px -2px var(--signal-glow), 0 2px 8px -4px rgba(0,0,0,0.5);
}
.vrs-btn__secondary:active:not(:disabled) { transform: translateY(1px); background-image: none; background-color: var(--surface-card); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }

/* ---- Ghost: quiet until touched ---- */
.vrs-btn__ghost { background: transparent; color: var(--text-body); }
.vrs-btn__ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-strong); }
.vrs-btn__ghost:active:not(:disabled) { transform: translateY(1px); background: var(--surface-card); }

/* ---- Danger: armed ---- */
.vrs-btn__danger {
  color: var(--rejected-500); background: transparent;
  border-color: color-mix(in srgb, var(--rejected-500) 38%, transparent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.vrs-btn__danger:hover:not(:disabled) { background: var(--rejected-bg); border-color: color-mix(in srgb, var(--rejected-500) 62%, transparent); box-shadow: 0 0 14px -2px color-mix(in srgb, var(--rejected-500) 40%, transparent); }
.vrs-btn__danger:active:not(:disabled) { transform: translateY(1px); background: color-mix(in srgb, var(--rejected-500) 18%, transparent); }

.vrs-btn__full { width: 100%; }
.vrs-btn__spin { width: 1em; height: 1em; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: vrs-btn-spin 0.6s linear infinite; }
@keyframes vrs-btn-spin { to { transform: rotate(360deg); } }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-button-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-button-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/**
 * Verasig primary button.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  iconLeft = null,
  iconRight = null,
  loading = false,
  fullWidth = false,
  disabled = false,
  as = 'button',
  type = 'button',
  className = '',
  children,
  ...rest
}) {
  const Tag = as
  const cls = [
    'vrs-btn',
    `vrs-btn__${variant}`,
    size !== 'md' ? `vrs-btn__sz-${size}` : '',
    fullWidth ? 'vrs-btn__full' : '',
    loading ? 'vrs-btn__loading' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <Tag
      className={cls}
      type={Tag === 'button' ? type : undefined}
      disabled={Tag === 'button' ? disabled || loading : undefined}
      {...rest}
    >
      {loading && <span className="vrs-btn__spin" aria-hidden="true" />}
      {!loading && iconLeft}
      {children}
      {!loading && iconRight}
    </Tag>
  )
}
