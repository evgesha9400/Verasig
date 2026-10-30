import crypto from 'node:crypto'

// Stripe stand-ins for the checkout spec.
//
// The browser never reaches Stripe: the billing API calls are intercepted and
// answered with stub Checkout and portal pages served at the app's origin. The
// plan then changes the way production changes it, through a webhook signed
// with E2E_STRIPE_WEBHOOK_SECRET (the backend's VERASIG_STRIPE_WEBHOOK_SECRET).

const CHECKOUT_PATH = '/e2e/stripe-checkout'
const PORTAL_PATH = '/e2e/stripe-portal'
export const STUB_SESSION_ID = 'cs_test_e2e'

function stubPage(title, body) {
  const style =
    'body{margin:0;background:#0b0d10;color:#e8eaed;font:15px sans-serif;display:flex;' +
    'align-items:center;justify-content:center;min-height:100vh}' +
    'main{width:420px;border:1px solid #333;padding:32px}' +
    'label{display:block;font-size:12px;color:#999;margin:16px 0 6px}' +
    'input{width:100%;box-sizing:border-box;padding:10px;background:#000;border:1px solid #444;color:#fff}' +
    'button,a{display:block;width:100%;margin-top:24px;padding:12px;text-align:center;' +
    'background:#fff;color:#000;border:0;font-size:14px;cursor:pointer;text-decoration:none}'
  return (
    `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>` +
    `<style>${style}</style></head><body><main>${body}</main></body></html>`
  )
}

function checkoutHtml(returnUrl) {
  const form =
    '<form id="payment-form" autocomplete="off"><h1>Verasig Trader</h1>' +
    '<p>7 days free, then $49.00 per month</p>' +
    '<label for="cardNumber">Card number</label><input id="cardNumber" name="cardNumber">' +
    '<label for="cardExpiry">Expiry</label><input id="cardExpiry" name="cardExpiry">' +
    '<label for="cardCvc">CVC</label><input id="cardCvc" name="cardCvc">' +
    '<label for="billingName">Name on card</label><input id="billingName" name="billingName">' +
    '<button type="submit">Subscribe</button></form>'
  const script =
    `<script>document.getElementById('payment-form').onsubmit=(e)=>{` +
    `e.preventDefault();window.location.href=${JSON.stringify(returnUrl)};};</script>`
  return stubPage('Stripe Checkout (stub)', form + script)
}

function portalHtml(returnUrl) {
  return stubPage(
    'Stripe billing portal (stub)',
    `<h1>Verasig billing</h1><p>Verasig Trader</p>` +
      `<a href=${JSON.stringify(returnUrl)}>Return to Verasig</a>`
  )
}

// `**/billing/...` matches both the deployed `/api/billing/...` and the local
// API on :8000, which has no `/api` prefix.
export async function stubStripeCheckout(page, baseUrl) {
  const checkoutUrl = `${baseUrl}${CHECKOUT_PATH}?session=${STUB_SESSION_ID}`
  const returnUrl = `${baseUrl}/app?checkout=success&session_id=${STUB_SESSION_ID}`
  const portalUrl = `${baseUrl}${PORTAL_PATH}`
  await page.route('**/billing/checkout', (route) =>
    route.fulfill({ json: { url: checkoutUrl, id: STUB_SESSION_ID } })
  )
  await page.route('**/billing/portal', (route) =>
    route.fulfill({ json: { url: portalUrl } })
  )
  await page.route(`**${CHECKOUT_PATH}*`, (route) =>
    route.fulfill({
      contentType: 'text/html; charset=utf-8',
      body: checkoutHtml(returnUrl)
    })
  )
  await page.route(`**${PORTAL_PATH}*`, (route) =>
    route.fulfill({
      contentType: 'text/html; charset=utf-8',
      body: portalHtml(`${baseUrl}/app`)
    })
  )
}

// Stripe's v1 scheme: HMAC-SHA256 of "<unix seconds>.<raw body>" with the secret.
export function stripeSignature(
  body,
  secret,
  timestamp = Math.floor(Date.now() / 1000)
) {
  const digest = crypto
    .createHmac('sha256', secret)
    .update(`${timestamp}.${body}`)
    .digest('hex')
  return `t=${timestamp},v1=${digest}`
}

export function checkoutCompletedEvent(userId) {
  return JSON.stringify({
    id: 'evt_e2e_checkout_completed',
    object: 'event',
    type: 'checkout.session.completed',
    data: {
      object: {
        id: STUB_SESSION_ID,
        object: 'checkout.session',
        mode: 'subscription',
        status: 'complete',
        payment_status: 'paid',
        client_reference_id: userId,
        customer: `cus_e2e_${userId.slice(0, 8)}`,
        subscription: `sub_e2e_${userId.slice(0, 8)}`,
        metadata: { user_id: userId, plan: 'trader' }
      }
    }
  })
}

// Posts the webhook Stripe would send when the stub Checkout completes.
export function postStripeWebhook(request, apiUrl, body, secret) {
  return request.post(`${apiUrl}/billing/webhook`, {
    data: body,
    headers: {
      'content-type': 'application/json',
      'stripe-signature': stripeSignature(body, secret)
    }
  })
}

export function activateTraderByWebhook(request, apiUrl, userId, secret) {
  return postStripeWebhook(request, apiUrl, checkoutCompletedEvent(userId), secret)
}
