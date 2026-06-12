const CSS = `
.vrs-select { position: relative; display: flex; flex-direction: column; gap: 6px; }
.vrs-select__label { font-family: var(--font-sans); font-size: var(--text-xs); font-weight: var(--fw-medium); color: var(--text-body); }
.vrs-select__box { position: relative; display: flex; align-items: center; }
.vrs-select select {
  appearance: none; width: 100%; height: 38px;
  padding: 0 36px 0 12px;
  font-family: var(--font-sans); font-size: var(--text-sm); color: var(--text-strong);
  background: var(--surface-sunken); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
}
.vrs-select select:hover { border-color: var(--border-strong); }
.vrs-select select:focus-visible { outline: none; border-color: var(--border-focus); box-shadow: 0 0 0 3px var(--accent-quiet); }
.vrs-select__chev {
  position: absolute; right: 12px; pointer-events: none; color: var(--text-muted);
  display: inline-flex;
}
.vrs-select__chev svg { width: 15px; height: 15px; display:block; }
.vrs-select.is-disabled { opacity: 0.5; pointer-events: none; }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-select-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-select-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/** Native select, styled. Pass `options` or `children`. */
export function Select({
  label,
  options,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-select', disabled ? 'is-disabled' : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={cls}>
      {label && <label className="vrs-select__label">{label}</label>}
      <div className="vrs-select__box">
        <select disabled={disabled} {...rest}>
          {options
            ? options.map((o) => {
                const value = typeof o === 'string' ? o : o.value
                const text = typeof o === 'string' ? o : o.label
                return (
                  <option key={value} value={value}>
                    {text}
                  </option>
                )
              })
            : children}
        </select>
        <span className="vrs-select__chev">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </div>
    </div>
  )
}
