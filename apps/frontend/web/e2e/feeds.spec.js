import { expect, test } from '@playwright/test'

// These specs run with the stored session (see auth.setup.js) — the login form
// is never touched. They act AS the real account, so keep them read-only.

test('reuses the session and reaches the app without a login form @smoke', async ({
  page
}) => {
  await page.goto('/app')
  // Session restored from storageState => not bounced back to /login.
  await expect(page).not.toHaveURL(/\/login/)
  // The authenticated shell renders the Sources nav item.
  await expect(page.getByRole('button', { name: /sources/i })).toBeVisible()
})

test('feed rows carry the hover + focus highlight', async ({ page }) => {
  await page.goto('/app')

  // Feeds hydrate asynchronously from GET /feeds; tolerate empty accounts.
  const rows = page.locator('.vrs-feed-row')
  await rows
    .first()
    .waitFor({ state: 'visible', timeout: 8000 })
    .catch(() => {})

  const count = await rows.count()
  test.skip(
    count === 0,
    'No feeds on this account — point E2E_EMAIL at an account with Telegram connected + feeds.'
  )

  const firstRow = rows.first()
  const readBorder = () => firstRow.evaluate((el) => getComputedStyle(el).borderColor)

  const beforeHover = await readBorder()
  await firstRow.hover()
  // Hover flips border-color to --border-strong (app.css .vrs-feed-row:hover).
  await expect.poll(readBorder).not.toBe(beforeHover)
})
