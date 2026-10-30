import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Tooltip } from './Tooltip.jsx'

describe('Tooltip', () => {
  it('describes its trigger by the tooltip id', () => {
    const { getByRole, getByText } = render(
      <Tooltip label="Copy link">
        <button aria-describedby="extra">Copy</button>
      </Tooltip>
    )
    const tipId = getByRole('tooltip').id
    expect(tipId).not.toBe('')
    expect(getByText('Copy').getAttribute('aria-describedby')).toBe(`extra ${tipId}`)
  })

  it('dismisses on Escape while hovered and resets on mouseleave', () => {
    const { container } = render(
      <Tooltip label="Copy link">
        <button>Copy</button>
      </Tooltip>
    )
    const wrap = container.querySelector('.vrs-tip')
    fireEvent.mouseEnter(wrap)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(wrap.getAttribute('data-dismissed')).toBe('true')
    fireEvent.mouseLeave(wrap)
    expect(wrap.hasAttribute('data-dismissed')).toBe(false)
  })

  it('makes the shown tip hoverable with a gap bridge', () => {
    render(
      <Tooltip label="x">
        <button>y</button>
      </Tooltip>
    )
    const css = document.getElementById('vrs-tip-css').textContent
    expect(css).toMatch(
      /\.vrs-tip:hover \.vrs-tip__pop[^{]*\{[^}]*pointer-events: auto/
    )
    expect(css).toContain('.vrs-tip__pop::before')
    expect(css).toContain('.vrs-tip[data-dismissed] .vrs-tip__pop')
  })
})
