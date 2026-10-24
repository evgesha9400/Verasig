import { act, fireEvent, render } from '@testing-library/react'
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

describe('Popover Escape dismissal', () => {
  it('hides the panel on Escape while engaged and returns focus to the trigger', () => {
    const { container, getByText } = render(
      <Popover role="dialog" trigger={<span>t</span>}>
        <button>Act</button>
      </Popover>
    )
    const wrap = container.querySelector('.vrs-pop')
    const action = getByText('Act')
    act(() => action.focus())
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(wrap.getAttribute('data-dismissed')).toBe('true')
    expect(document.activeElement).toBe(container.querySelector('.vrs-pop__trigger'))
    expect(container.querySelector('[role="dialog"]')).not.toBeNull()

    fireEvent.mouseLeave(wrap)
    expect(wrap.hasAttribute('data-dismissed')).toBe(false)
  })
})
