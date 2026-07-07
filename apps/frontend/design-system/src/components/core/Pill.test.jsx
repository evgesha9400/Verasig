import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Pill } from './Pill.jsx'

const classOf = (ui) => render(ui).container.firstChild.className

describe('Pill', () => {
  it('renders its children inside a pill span', () => {
    const { container, getByText } = render(<Pill tone="accent">Recommended</Pill>)
    expect(getByText('Recommended')).toBeTruthy()
    expect(container.querySelector('span.vrs-pill')).toBeTruthy()
  })

  it('applies tone, variant, size and numeric modifiers', () => {
    expect(classOf(<Pill tone="accent">x</Pill>)).toContain('vrs-pill__accent')
    expect(
      classOf(
        <Pill tone="pending" variant="outline">
          x
        </Pill>
      )
    ).toContain('vrs-pill__outline')
    expect(classOf(<Pill size="xs">x</Pill>)).toContain('vrs-pill__xs')
    expect(classOf(<Pill numeric>x</Pill>)).toContain('vrs-pill__num')
  })

  it('defaults to the soft variant with no xs or numeric modifier', () => {
    const c = classOf(<Pill tone="accent">x</Pill>)
    expect(c).toContain('vrs-pill__soft')
    expect(c).not.toContain('vrs-pill__xs')
    expect(c).not.toContain('vrs-pill__num')
  })

  it('passes arbitrary props such as style through to the span', () => {
    const { container } = render(<Pill style={{ marginLeft: 8 }}>x</Pill>)
    expect(container.firstChild.style.marginLeft).toBe('8px')
  })

  // CSS-only: the outline variant must render a visible border for profit/loss
  // tones, not the transparent placeholder. Assert the injected rules exist.
  it('gives profit and loss tones an outline border color', () => {
    render(<Pill tone="profit">x</Pill>)
    const css = document.getElementById('vrs-pill-css').textContent
    expect(css).toContain('.vrs-pill__profit.vrs-pill__outline { border-color:')
    expect(css).toContain('.vrs-pill__loss.vrs-pill__outline { border-color:')
  })
})
