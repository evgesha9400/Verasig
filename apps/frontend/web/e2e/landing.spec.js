import { expect, test } from '@playwright/test'

// Read-only: these run against the live site after every deploy (@smoke).

test('landing page loads @smoke', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText(
    'Verify the signal'
  )
  await expect(page.getByRole('link', { name: /sign up/i }).first()).toHaveAttribute(
    'href',
    '/signup'
  )
})

test('deep link loads the web app @smoke', async ({ page }) => {
  const response = await page.goto('/app')
  expect(response?.status()).toBe(200)
  await expect(page.locator('#root')).toBeAttached()
})

test('pricing section lists the plans @smoke', async ({ page }) => {
  await page.goto('/#pricing')
  const pricing = page.locator('#pricing')
  for (const name of ['Free check', 'Trader', 'Desk']) {
    await expect(pricing.getByRole('heading', { level: 3, name })).toBeVisible()
  }
  const trader = pricing.getByRole('article', { name: 'Trader' })
  await expect(trader).toContainText('$49')
  await expect(
    trader.getByRole('link', { name: /start 7-day trial/i })
  ).toHaveAttribute('href', '/signup?plan=trader')
  await expect(
    page.getByRole('banner').getByRole('link', { name: 'Pricing' })
  ).toHaveAttribute('href', '#pricing')
})
