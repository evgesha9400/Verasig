import { InteractiveCard } from './InteractiveCard.jsx'

const CSS = `
.vrs-choice-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.vrs-choice-card__body {
  flex: 1;
  min-width: 0;
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-choice-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-choice-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

export function ChoiceCard({
  selected = false,
  onClick,
  className = '',
  children,
  ...rest
}) {
  return (
    <InteractiveCard
      selected={selected}
      aria-pressed={selected}
      onClick={onClick}
      className={['vrs-choice-card', className].filter(Boolean).join(' ')}
      {...rest}
    >
      <span className="vrs-choice-card__body">{children}</span>
    </InteractiveCard>
  )
}
