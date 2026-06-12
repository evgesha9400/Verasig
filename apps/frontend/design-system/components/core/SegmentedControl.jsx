const CSS = `
.vrs-seg {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
}
.vrs-seg__radio {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 30px;
  height: 26px;
  padding: 0 9px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--fw-medium);
  line-height: 1;
  white-space: nowrap;
  transition:
    background var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out),
    transform var(--dur-instant) var(--ease-out);
}
.vrs-seg__radio:hover:not(:disabled) {
  color: var(--text-strong);
  background: var(--surface-hover);
}
.vrs-seg__radio[aria-checked='true'] {
  background-color: var(--surface-card);
  background-image: linear-gradient(180deg, color-mix(in srgb, var(--surface-card) 90%, #fff), var(--surface-card));
  color: var(--accent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 1px 1.5px rgba(0,0,0,0.3);
}
.vrs-seg__radio:active:not(:disabled) {
  transform: translateY(1px);
}
.vrs-seg__radio:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
.vrs-seg__radio:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.vrs-seg__radio svg {
  width: 15px;
  height: 15px;
  flex: none;
}
.vrs-seg__radio--icon {
  width: 30px;
  padding: 0;
}
.vrs-seg__sm .vrs-seg__radio {
  min-width: 28px;
  height: 24px;
  padding-inline: 8px;
  font-size: var(--text-2xs);
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-seg-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-seg-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

function optionValue(option) {
  return option.value ?? option.id
}

function nextEnabledOption(options, current, direction) {
  const enabled = options.filter((option) => !option.disabled)
  if (enabled.length === 0) return null
  const index = enabled.findIndex((option) => optionValue(option) === current)
  const nextIndex =
    index === -1 ? 0 : (index + direction + enabled.length) % enabled.length
  return enabled[nextIndex]
}

export function SegmentedControl({
  value,
  onChange,
  options,
  label,
  size = 'md',
  iconOnly = false,
  className = '',
  ...rest
}) {
  function choose(next) {
    if (next == null || next === value) return
    onChange && onChange(next)
  }

  function onKeyDown(e) {
    const keyDirections = {
      ArrowRight: 1,
      ArrowDown: 1,
      ArrowLeft: -1,
      ArrowUp: -1
    }
    const direction = keyDirections[e.key]
    if (!direction && e.key !== 'Home' && e.key !== 'End') return
    e.preventDefault()
    const enabled = options.filter((option) => !option.disabled)
    const next =
      e.key === 'Home'
        ? enabled[0]
        : e.key === 'End'
          ? enabled[enabled.length - 1]
          : nextEnabledOption(options, value, direction)
    choose(next && optionValue(next))
  }

  const cls = ['vrs-seg', size !== 'md' ? `vrs-seg__${size}` : '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={cls}
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      {...rest}
    >
      {options.map((option) => {
        const nextValue = optionValue(option)
        const selected = value === nextValue
        const hasText = !iconOnly && option.label
        const radioCls = ['vrs-seg__radio', !hasText ? 'vrs-seg__radio--icon' : '']
          .filter(Boolean)
          .join(' ')

        return (
          <button
            key={nextValue}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={option.ariaLabel || option.label}
            title={option.title || option.label}
            className={radioCls}
            disabled={option.disabled}
            tabIndex={selected ? 0 : -1}
            onClick={() => choose(nextValue)}
          >
            {option.icon}
            {hasText && <span>{option.label}</span>}
          </button>
        )
      })}
    </div>
  )
}
