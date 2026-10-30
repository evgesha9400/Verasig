import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createCheckout, openBillingPortal } from './billingApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('billingApi', () => {
  it('creates a Checkout session for a plan and billing interval', async () => {
    const session = { url: 'https://checkout.stripe.com/c/pay/cs_1', id: 'cs_1' }
    fetch.mockResolvedValueOnce(jsonResponse(session))

    const body = await createCheckout('jwt-token', 'trader', 'year')

    expect(body).toEqual(session)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/billing/checkout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ plan: 'trader', interval: 'year' })
    })
  })

  it('opens the billing portal without a body', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ url: 'https://billing.stripe.com/p/1' }))

    const body = await openBillingPortal('jwt-token')

    expect(body.url).toBe('https://billing.stripe.com/p/1')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/billing/portal', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('surfaces the API error when billing is not configured', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'BILLING_NOT_CONFIGURED', message: 'Billing is off' } },
        503
      )
    )

    await expect(createCheckout('jwt-token', 'trader', 'month')).rejects.toMatchObject({
      status: 503,
      code: 'BILLING_NOT_CONFIGURED'
    })
  })
})
