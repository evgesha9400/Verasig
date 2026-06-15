import { render, cleanup, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ThemeProvider } from './ThemeProvider.jsx'

function accentTokens() {
  const style = document.documentElement.style
  return {
    accent: style.getPropertyValue('--accent'),
    hover: style.getPropertyValue('--accent-hover'),
    press: style.getPropertyValue('--accent-press'),
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
  })

  it('uses the azure accent in light theme', async () => {
    await renderTheme('light')

    const tokens = accentTokens()
    expect(tokens.accent).toBe('#5197FF')
    expect(tokens.hover).toBe('#82B6FF')
    expect(tokens.press).toBe('#2F6FE0')
  })

  it('repoints the signal ramp to azure in light theme so direct signal users are not lime', async () => {
    await renderTheme('light')

    const tokens = accentTokens()
    expect(tokens.signal500).toBe('#5197FF')
    expect(tokens.signal600).toBe('#2F6FE0')
    expect(tokens.verified).toBe('#5197FF')
  })
})
