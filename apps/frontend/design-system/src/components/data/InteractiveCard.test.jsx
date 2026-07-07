import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { InteractiveCard } from './InteractiveCard.jsx'
import { Card } from './Card.jsx'

const classOf = (ui) => render(ui).container.firstChild.className

describe('InteractiveCard', () => {
  it('keeps interactive styling when selected (does not replace it)', () => {
    const cls = classOf(<InteractiveCard selected>x</InteractiveCard>)
    expect(cls).toContain('vrs-card__interactive')
    expect(cls).toContain('vrs-card__selected')
  })

  it('is interactive when not selected', () => {
    const cls = classOf(<InteractiveCard>x</InteractiveCard>)
    expect(cls).toContain('vrs-card__interactive')
    expect(cls).not.toContain('vrs-card__selected')
  })
})

describe('Card interactive specificity (CSS-only)', () => {
  // The cursor/hover conflict is a pure CSS cascade fix; assert the injected
  // stylesheet raises specificity via the doubled `.vrs-card.vrs-card__interactive`.
  it('scopes interactive rules with raised specificity', () => {
    render(<Card interactive>x</Card>)
    const css = document.getElementById('vrs-card-css').textContent
    expect(css).toContain('.vrs-card.vrs-card__interactive { cursor: pointer; }')
    expect(css).toContain('.vrs-card.vrs-card__interactive:hover')
  })
})
