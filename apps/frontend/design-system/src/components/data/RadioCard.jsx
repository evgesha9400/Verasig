import { InteractiveCard } from './InteractiveCard.jsx'

const CSS = `
.vrs-radio-card__mark {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  border-radius: 50%;
  border: 1.5px solid var(--border-strong);
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.vrs-radio-card[aria-checked='true'] .vrs-radio-card__mark {
  border-color: var(--accent);
}
.vrs-radio-card[aria-checked='true'] .vrs-radio-card__mark::after {
  content: '';
  display: block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--accent);
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-radio-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-radio-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

export function RadioCard({
  selected = false,
  onClick,
  as,
  className = '',
  children,
  ...rest
}) {
  function onKeyDown(event) {
    rest.onKeyDown && rest.onKeyDown(event)
    if (event.defaultPrevented || as !== 'div') return
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onClick && onClick(event)
  }

  return (
    <InteractiveCard
      as={as}
      role="radio"
      aria-checked={selected}
      tabIndex={as === 'div' ? 0 : undefined}
      selected={selected}
      className={['vrs-radio-card', className].filter(Boolean).join(' ')}
      {...rest}
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      <span className="vrs-radio-card__mark" aria-hidden="true" />
      {children}
    </InteractiveCard>
  )
}
