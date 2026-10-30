import { expect, test } from '@playwright/test'

// Creates a user, so it never runs against the live site (no @smoke tag).
test.use({ storageState: { cookies: [], origins: [] } })

test('sign-up form creates an account and opens the app', async ({ page }) => {
  await page.goto('/signup')
  await page.getByLabel(/full name/i).fill('Test Runner')
  await page.getByLabel(/email/i).fill(`e2e-form-${Date.now()}@example.com`)
  await page.getByLabel('Password', { exact: true }).fill(crypto.randomUUID())
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/app/)
  await expect(page.getByRole('button', { name: /sources/i })).toBeVisible()
})
