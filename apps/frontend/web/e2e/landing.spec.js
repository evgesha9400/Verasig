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
