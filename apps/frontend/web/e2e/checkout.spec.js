import { expect, test } from '@playwright/test'

import {
  activateTraderByWebhook,
  checkoutCompletedEvent,
  postStripeWebhook,
  stubStripeCheckout
} from './stripe-stub.js'
import { API_URL } from './urls.js'

// Signs up a new user and changes its plan, so it never runs against the live
// site (no @smoke tag). Stripe is stubbed; the plan changes through a signed
// webhook, the way production changes it.

const TEST_CARD_NUMBER = '4242 4242 4242 4242'
const TEST_CARD_EXPIRY = '12/34'
const TEST_CARD_CVC = '123'
const TEST_CARD_HOLDER = 'Test Runner'
const TOKEN_KEY = 'vrs-auth-token-1'
const WEBHOOK_SECRET = process.env.E2E_STRIPE_WEBHOOK_SECRET

test.use({ storageState: { cookies: [], origins: [] } })

test.skip(
  !WEBHOOK_SECRET && !process.env.CI,
  'Set E2E_STRIPE_WEBHOOK_SECRET in e2e/.env to the backend VERASIG_STRIPE_WEBHOOK_SECRET.'
)

test.beforeEach(() => {
  expect(WEBHOOK_SECRET, 'E2E_STRIPE_WEBHOOK_SECRET is not set.').toBeTruthy()
})

// The user id is the `sub` claim of the JWT the app stored at signup.
async function signedInUserId(page) {
  const token = await page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY)
  const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString())
  return payload.sub
}

async function signUpForTrader(page) {
  await page.goto('/signup?plan=trader')
  await page.getByLabel(/full name/i).fill(TEST_CARD_HOLDER)
  await page.getByLabel(/email/i).fill(`e2e-checkout-${Date.now()}@example.com`)
  await page.getByLabel('Password', { exact: true }).fill(crypto.randomUUID())
  await page.getByRole('button', { name: 'Create account' }).click()
}

async function payOnStubCheckout(page) {
  await page.waitForURL(/\/e2e\/stripe-checkout/)
  await page.locator('#cardNumber').fill(TEST_CARD_NUMBER)
  await page.locator('#cardExpiry').fill(TEST_CARD_EXPIRY)
  await page.locator('#cardCvc').fill(TEST_CARD_CVC)
  await page.locator('#billingName').fill(TEST_CARD_HOLDER)
  await page.getByRole('button', { name: 'Subscribe' }).click()
}

async function openSettings(page) {
  await page.getByRole('button', { name: new RegExp(TEST_CARD_HOLDER) }).click()
  await page.getByRole('menuitem', { name: 'Account settings' }).click()
}

test.describe('Trader checkout', () => {
  test.afterEach(({ page }) => page.unrouteAll({ behavior: 'ignoreErrors' }))

  test('signup with ?plan=trader pays on Checkout and lands on Trader', async ({
    page,
    request,
    baseURL
  }) => {
    await stubStripeCheckout(page, baseURL)

    await signUpForTrader(page)
    await payOnStubCheckout(page)
    await page.waitForURL(/\/app/)
    const webhook = await activateTraderByWebhook(
      request,
      API_URL,
      await signedInUserId(page),
      WEBHOOK_SECRET
    )
    expect(webhook.status()).toBe(200)
    await expect(page.getByText('Trader activated')).toBeVisible({ timeout: 15_000 })
    await expect(page).not.toHaveURL(/checkout=/)

    await openSettings(page)
    const traderCard = page.locator('.vrs-plan', {
      has: page.getByRole('heading', { name: 'Trader' })
    })
    await expect(traderCard.getByText('Current')).toBeVisible()
    await page.getByRole('button', { name: 'Manage billing' }).click()
    await page.waitForURL(/\/e2e\/stripe-portal/)
    await page.getByRole('link', { name: 'Return to Verasig' }).click()
    await page.waitForURL(/\/app/)
  })

  test('the webhook rejects a payload with a bad signature', async ({ request }) => {
    const response = await postStripeWebhook(
      request,
      API_URL,
      checkoutCompletedEvent(crypto.randomUUID()),
      'whsec_wrong_secret'
    )

    expect(response.status()).toBe(400)
  })
})
