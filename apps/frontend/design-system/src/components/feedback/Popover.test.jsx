import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Popover } from './Popover.jsx'

describe('Popover hover-bridge', () => {
  it('reflects the side prop on the panel', () => {
    const { container } = render(
      <Popover side="top" trigger={<button>t</button>}>
        body
      </Popover>
    )
    const panel = container.querySelector('.vrs-pop__panel')
    expect(panel.getAttribute('data-side')).toBe('top')
  })

  // CSS-only: the bridge (::before) must sit on the edge facing the trigger for
  // every side. Assert the injected per-side rules place it correctly.
  it('places the bridge on the trigger-facing edge per side', () => {
    render(<Popover trigger={<button>t</button>}>body</Popover>)
    const css = document.getElementById('vrs-pop-css').textContent
    expect(css).toContain("[data-side='bottom']::before")
    expect(css).toContain("[data-side='top']::before")
    expect(css).toContain("[data-side='left']::before")
    expect(css).toContain("[data-side='right']::before")
    // top-side panel opens above the trigger → bridge on its bottom edge
    const topRule = css.slice(css.indexOf("[data-side='top']::before"))
    expect(topRule.slice(0, 80)).toContain('bottom: -10px')
  })
})
