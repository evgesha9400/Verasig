import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { Pricing } from './MarketingView.jsx'

function renderPricing() {
  render(
    <MemoryRouter>
      <Pricing />
    </MemoryRouter>
  )
}

describe('Pricing', () => {
  it('shows the three plans with their prices', () => {
    renderPricing()
    const plans = screen.getAllByRole('article')

    expect(plans.map((plan) => within(plan).getByRole('heading').textContent)).toEqual([
      'Free check',
      'Trader',
      'Desk'
    ])
    expect(plans[0].textContent).toContain('$0')
    expect(plans[1].textContent).toContain('$49/month')
    expect(plans[1].textContent).toContain('or $39/month billed yearly')
    expect(plans[1].textContent).toContain('7-day trial, card required')
    expect(plans[2].textContent).toContain('$149/month')
  })

  it('links Free and Trader to signup and keeps Desk unpurchasable', () => {
    renderPricing()
    const trader = screen.getByRole('article', { name: 'Trader' })
    const desk = screen.getByRole('article', { name: 'Desk' })

    expect(
      screen.getByRole('link', { name: 'Start a free check' }).getAttribute('href')
    ).toBe('/signup')
    expect(
      within(trader)
        .getByRole('link', { name: 'Start 7-day trial' })
        .getAttribute('href')
    ).toBe('/signup?plan=trader')
    expect(within(desk).queryByRole('link')).toBeNull()
    expect(within(desk).getByRole('button', { name: 'Coming soon' }).disabled).toBe(
      true
    )
  })
})
