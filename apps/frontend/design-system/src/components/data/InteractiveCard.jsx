import { Card } from './Card.jsx'

const CSS = `
.vrs-interactive-card {
  display: block;
  color: inherit;
}
`

if (
  typeof document !== 'undefined' &&
  !document.getElementById('vrs-interactive-card-css')
) {
  const s = document.createElement('style')
  s.id = 'vrs-interactive-card-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

export function InteractiveCard({
  as,
  href,
  selected = false,
  className = '',
  children,
  ...rest
}) {
  const tag = as || (href ? 'a' : 'button')
  return (
    <Card
      as={tag}
      href={tag === 'a' ? href : undefined}
      interactive
      selected={selected}
      padded={false}
      className={['vrs-interactive-card', className].filter(Boolean).join(' ')}
      {...rest}
    >
      {children}
    </Card>
  )
}
