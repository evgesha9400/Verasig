import { post } from './client.js'

// Starts a Stripe Checkout for `plan` billed per `interval` ('month' | 'year').
// Resolves to { url, id }; the caller redirects the browser to `url`.
export function createCheckout(token, plan, interval) {
  return post('/billing/checkout', token, { plan, interval })
}

// Opens the Stripe customer portal (cancel, resume, card, invoices). Resolves to { url }.
export function openBillingPortal(token) {
  return post('/billing/portal', token)
}
