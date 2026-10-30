// Full-page navigation away from the SPA (Stripe Checkout and the billing portal).
// Kept as its own module so tests can replace it.
export function redirectTo(url) {
  window.location.assign(url)
}
