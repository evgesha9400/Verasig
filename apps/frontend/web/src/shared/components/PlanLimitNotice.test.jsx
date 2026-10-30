import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PlanLimitNotice } from './PlanLimitNotice.jsx'

describe('PlanLimitNotice', () => {
  it('renders nothing unless shown', () => {
    const { container } = render(
      <PlanLimitNotice shown={false} total={644} limit={200} plan="free" />
    )
    expect(container.firstChild).toBeNull()
  })

  it('states the limit, total and plan when shown', () => {
    render(
      <PlanLimitNotice shown total={644} limit={200} plan="free" onUpgrade={() => {}} />
    )
    expect(screen.getByText(/200 most recent of 644 detected signals/)).toBeTruthy()
    expect(screen.getByText(/Free check/)).toBeTruthy()
  })

  it('fires onUpgrade when Upgrade is clicked', () => {
    const onUpgrade = vi.fn()
    render(
      <PlanLimitNotice
        shown
        total={644}
        limit={200}
        plan="free"
        onUpgrade={onUpgrade}
      />
    )
    fireEvent.click(screen.getByText('Upgrade'))
    expect(onUpgrade).toHaveBeenCalledTimes(1)
  })
})
