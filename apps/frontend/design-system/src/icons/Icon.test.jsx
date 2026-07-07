import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Icon } from './Icon.jsx'

afterEach(() => vi.restoreAllMocks())

describe('Icon unknown name', () => {
  it('warns (dev-only) when an unknown icon name is requested', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const { container } = render(<Icon name="definitely-not-an-icon" />)
    expect(warn).toHaveBeenCalledTimes(1)
    expect(warn.mock.calls[0][0]).toContain('definitely-not-an-icon')
    // still renders a safe svg
    expect(container.querySelector('svg')).toBeTruthy()
  })

  it('does not warn for a known icon name', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    render(<Icon name="settings" />)
    expect(warn).not.toHaveBeenCalled()
  })
})
