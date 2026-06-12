import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Marketing from './MarketingView.jsx'

describe('Marketing landing', () => {
  it('renders the hero headline', () => {
    render(<Marketing />)
    const h1 = screen.getByRole('heading', { level: 1 })
    expect(h1.textContent).toContain('Verify the signal')
    expect(h1.textContent).toContain('before you trade it.')
  })

  it('renders the eight pipeline steps', () => {
    render(<Marketing />)
    for (const step of [
      'Connect',
      'Backfill',
      'Label',
      'Distill',
      'Verify',
      'Route',
      'Risk',
      'Backtest'
    ]) {
      expect(screen.getAllByText(step).length).toBeGreaterThan(0)
    }
  })

  it('points Sign up CTAs at the app with the signup deep-link', () => {
    render(<Marketing />)
    const signups = screen.getAllByRole('link', { name: /sign up/i })
    expect(signups.length).toBeGreaterThan(0)
    for (const link of signups) {
      expect(link.getAttribute('href')).toBe('http://localhost:5173/?signup=1')
    }
  })

  it('points Log in CTAs at the app root', () => {
    render(<Marketing />)
    const logins = screen.getAllByRole('link', { name: /log in/i })
    expect(logins.length).toBeGreaterThan(0)
    for (const link of logins) {
      expect(link.getAttribute('href')).toBe('http://localhost:5173/')
    }
  })
})
