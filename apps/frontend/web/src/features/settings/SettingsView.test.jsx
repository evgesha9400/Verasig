import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { redirectTo } from '../../shared/navigation.js'
import { SettingsView } from './SettingsView.jsx'

vi.mock('../../shared/navigation.js', () => ({ redirectTo: vi.fn() }))

const user = {
  firstName: 'Ada',
  lastName: 'Lovelace',
  email: 'ada@example.com',
  plan: 'free',
  subscriptionStatus: null,
  pendingEmail: null,
  cancelAt: null
}

const trader = { ...user, plan: 'trader', subscriptionStatus: 'trialing' }

function renderSettings(props = {}) {
  const onToast = vi.fn()
  render(
    <SettingsView
      authToken="jwt-token"
      user={user}
      onUpdateUser={vi.fn()}
      onToast={onToast}
      {...props}
    />
  )
  return { onToast }
}

function planCard(name) {
  return screen.getByRole('heading', { name }).closest('.vrs-plan')
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
  redirectTo.mockReset()
})

describe('SettingsView', () => {
  it('saves profile changes through the backend account API', async () => {
    const updated = { ...user, firstName: 'Grace', lastName: 'Hopper' }
    const onUpdateUser = vi.fn()

    fetch.mockResolvedValueOnce(jsonResponse(updated))

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={() => {}}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: ' Grace ' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: '   Hopper  ' }
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[0])

    await waitFor(() => {
      expect(onUpdateUser).toHaveBeenCalledWith(updated)
    })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        firstName: 'Grace',
        lastName: 'Hopper'
      })
    })
  })

  it('disables save when profile names are invalid', () => {
    const onUpdateUser = vi.fn()
    const onToast = vi.fn()

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={onToast}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: 'Ada123' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: 'Lovelace' }
    })

    expect(screen.getAllByRole('button', { name: 'Save' })[0].disabled).toBe(true)
    expect(onUpdateUser).not.toHaveBeenCalled()
    expect(screen.getByText(/may contain only letters/)).toBeTruthy()
  })

  it('cancels a pending email change through the backend', async () => {
    const pending = { ...user, pendingEmail: 'next@example.com' }
    const onUpdateUser = vi.fn()

    fetch.mockResolvedValueOnce(jsonResponse(user))

    render(
      <SettingsView
        authToken="jwt-token"
        user={pending}
        onUpdateUser={onUpdateUser}
        onToast={() => {}}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Cancel change' }))

    await waitFor(() => {
      expect(onUpdateUser).toHaveBeenCalledWith(user)
    })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user/email/cancel', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('surfaces backend validation errors in the toast path', async () => {
    const onUpdateUser = vi.fn()
    const onToast = vi.fn()

    fetch.mockResolvedValueOnce(
      jsonResponse({ error: { message: 'Names are not valid' } }, 422)
    )

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={onToast}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: 'Grace' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: 'Hopper' }
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[0])

    await waitFor(() => {
      expect(onUpdateUser).not.toHaveBeenCalled()
    })
    expect(onToast).toHaveBeenCalledWith(
      'rejected',
      'Account update failed',
      'Names are not valid'
    )
  })

  it('upgrades a free user to Trader through Stripe Checkout', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ url: 'https://checkout.stripe.com/c/pay/cs_1', id: 'cs_1' })
    )
    renderSettings()

    fireEvent.click(
      within(planCard('Trader')).getByRole('button', { name: 'Start 7-day trial' })
    )

    await waitFor(() =>
      expect(redirectTo).toHaveBeenCalledWith('https://checkout.stripe.com/c/pay/cs_1')
    )
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/billing/checkout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ plan: 'trader', interval: 'month' })
    })
  })

  it('offers yearly billing for Trader', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ url: 'https://stripe.test/y', id: 'cs_2' })
    )
    renderSettings()

    fireEvent.click(
      within(planCard('Trader')).getByRole('button', { name: /Pay yearly/ })
    )

    await waitFor(() =>
      expect(redirectTo).toHaveBeenCalledWith('https://stripe.test/y')
    )
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
      plan: 'trader',
      interval: 'year'
    })
  })

  it('disables the upgrade buttons while Checkout is being created', async () => {
    fetch.mockReturnValue(new Promise(() => {}))
    renderSettings()
    const start = within(planCard('Trader')).getByRole('button', {
      name: 'Start 7-day trial'
    })

    fireEvent.click(start)

    await waitFor(() => expect(start.disabled).toBe(true))
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('reports a Checkout failure in a toast', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ error: { message: 'Billing is not configured' } }, 503)
    )
    const { onToast } = renderSettings()

    fireEvent.click(
      within(planCard('Trader')).getByRole('button', { name: 'Start 7-day trial' })
    )

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        'rejected',
        'Billing unavailable',
        'Billing is not configured'
      )
    )
    expect(redirectTo).not.toHaveBeenCalled()
  })

  it('shows Desk as coming soon with no purchase button', () => {
    renderSettings()

    const desk = planCard('Desk')
    expect(within(desk).getByText('Coming soon')).toBeTruthy()
    expect(within(desk).queryByRole('button')).toBeNull()
  })

  it('marks Trader current and opens the billing portal for a subscriber', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ url: 'https://billing.stripe.com/p/1' }))
    renderSettings({ user: trader })

    expect(within(planCard('Trader')).getByText('Current')).toBeTruthy()
    expect(screen.getByText('Trial')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Manage billing' }))

    await waitFor(() =>
      expect(redirectTo).toHaveBeenCalledWith('https://billing.stripe.com/p/1')
    )
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/billing/portal', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('has no billing portal for a user who never subscribed', () => {
    renderSettings()

    expect(screen.queryByRole('button', { name: 'Manage billing' })).toBeNull()
  })

  it('shows the end date of a cancelled subscription from cancelAt', () => {
    renderSettings({ user: { ...trader, cancelAt: '2027-01-01T00:00:00Z' } })

    expect(screen.getByText('Cancelling')).toBeTruthy()
    expect(screen.getByText('Subscription ends Jan 1, 2027')).toBeTruthy()
    expect(screen.queryByText(/Jul 8/)).toBeNull()
  })

  it('warns about a failed payment and offers no second subscription', () => {
    renderSettings({ user: { ...user, subscriptionStatus: 'past_due' } })

    expect(screen.getByText('Payment failed')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Manage billing' })).toBeTruthy()
    expect(within(planCard('Trader')).queryByRole('button')).toBeNull()
  })

  it('offers Trader again after the subscription ended', () => {
    renderSettings({ user: { ...user, subscriptionStatus: 'canceled' } })

    expect(
      within(planCard('Trader')).getByRole('button', { name: 'Start 7-day trial' })
    ).toBeTruthy()
  })
})
