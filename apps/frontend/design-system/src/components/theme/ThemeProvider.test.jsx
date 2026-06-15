import { render, cleanup, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider, useTheme } from './ThemeProvider.jsx'

function accentTokens() {
  const style = document.documentElement.style
  return {
    accent: style.getPropertyValue('--accent'),
    hover: style.getPropertyValue('--accent-hover'),
    press: style.getPropertyValue('--accent-press'),
    accentText: style.getPropertyValue('--accent-text'),
    signal500: style.getPropertyValue('--signal-500'),
    signal600: style.getPropertyValue('--signal-600'),
    verified: style.getPropertyValue('--verified-500')
  }
}

function renderTheme(initialTheme) {
  render(
    <ThemeProvider initialTheme={initialTheme}>
      <div />
    </ThemeProvider>
  )
  return waitFor(() =>
    expect(document.documentElement.getAttribute('data-theme')).toBe(initialTheme)
  )
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.removeAttribute('style')
})
afterEach(cleanup)

describe('ThemeProvider accent palette', () => {
  it('uses the lime signal accent in dark theme', async () => {
    await renderTheme('dark')

    const tokens = accentTokens()
    expect(tokens.accent).toBe('#B9EE2E')
    expect(tokens.signal500).toBe('#B9EE2E')
    // accent-text is the readable foreground (lighter lime on dark surfaces)
    expect(tokens.accentText).toBe('#CBF457')
  })

  it('uses the azure accent in light theme', async () => {
    await renderTheme('light')

    const tokens = accentTokens()
    expect(tokens.accent).toBe('#5197FF')
    expect(tokens.hover).toBe('#82B6FF')
    expect(tokens.press).toBe('#2F6FE0')
    // accent-text must stay the darker azure (#2F6FE0 ~4.7:1 on white), NOT the
    // light hover #82B6FF (~2.1:1) the prototype used — keeps accent text legible.
    expect(tokens.accentText).toBe('#2F6FE0')
  })

  it('repoints the signal ramp to azure in light theme so direct signal users are not lime', async () => {
    await renderTheme('light')

    const tokens = accentTokens()
    expect(tokens.signal500).toBe('#5197FF')
    expect(tokens.signal600).toBe('#2F6FE0')
    expect(tokens.verified).toBe('#5197FF')
  })
})

describe('useTheme outside a provider', () => {
  it('throws instead of silently spinning up a competing theme state', () => {
    function Consumer() {
      useTheme()
      return null
    }

    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Consumer />)).toThrow(/ThemeProvider/)
    errorSpy.mockRestore()
  })
})
