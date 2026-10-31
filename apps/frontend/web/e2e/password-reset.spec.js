import { expect, test } from '@playwright/test'

import { MAIL_API_URL, messagesTo, waitForMessageTo } from './mailpit.js'
import { API_URL } from './urls.js'

// Creates a user and sends real mail to Mailpit, so it never runs against the
// live site (no @smoke tag).
const OLD_PASSWORD = 'an old e2e passphrase'
const NEW_PASSWORD = 'a brand new e2e passphrase'
const CONFIRMATION =
  'If an account exists for that address, a reset link is on its way.'

test.use({ storageState: { cookies: [], origins: [] } })

test.skip(
  !MAIL_API_URL && !process.env.CI,
  'Set E2E_MAIL_API_URL in e2e/.env to Mailpit (http://localhost:8025).'
)

test.beforeEach(() => {
  expect(MAIL_API_URL, 'E2E_MAIL_API_URL is not set.').toBeTruthy()
})

async function registerUser(request, email) {
  const response = await request.post(`${API_URL}/auth/register`, {
    data: { firstName: 'Test', lastName: 'Runner', email, password: OLD_PASSWORD }
  })
  expect(response.ok(), `register failed (HTTP ${response.status()})`).toBeTruthy()
}

async function askForResetLink(page, email) {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Forgot password?' }).click()
  await expect(page).toHaveURL(/\/forgot-password$/)
  // The URL changes before the route renders (React transition); wait for the page.
  await expect(page.getByRole('heading', { name: 'Reset your password' })).toBeVisible()
  await page.getByLabel(/email/i).fill(email)
  await page.getByRole('button', { name: 'Email me a reset link' }).click()
  await expect(page.getByText(CONFIRMATION)).toBeVisible()
}

// The link's origin is the backend's VERASIG_SITE_URL; open its path here.
function resetPathFrom(text) {
  const match = text.match(/https?:\/\/\S+\/reset-password\?token=\S+/)
  expect(match, `no reset link in the email:\n${text}`).toBeTruthy()
  const url = new URL(match[0])
  return `${url.pathname}${url.search}`
}

async function setNewPassword(page, password) {
  await page.getByLabel('New password', { exact: true }).fill(password)
  await page.getByLabel('Confirm new password').fill(password)
  await page.getByRole('button', { name: 'Set new password' }).click()
}

test('a forgotten password is reset through the emailed link', async ({
  page,
  request
}) => {
  const email = `e2e-reset-${Date.now()}@example.com`
  await registerUser(request, email)

  await askForResetLink(page, email)
  const message = await waitForMessageTo(email)
  expect(message.Subject).toBe('Reset your Verasig password')
  const resetPath = resetPathFrom(message.Text)

  await page.goto(resetPath)
  await setNewPassword(page, NEW_PASSWORD)
  await expect(page).toHaveURL(/\/login\?reset=1$/)
  await expect(page.getByText('Password updated')).toBeVisible()

  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(NEW_PASSWORD)
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/app/)

  // The link works once: the password it was minted for is gone.
  await page.goto(resetPath)
  await setNewPassword(page, OLD_PASSWORD)
  await expect(page.getByText('This link is invalid or has expired')).toBeVisible()
})

test('an unknown email gets the same answer and no mail', async ({ page }) => {
  const email = `e2e-reset-unknown-${Date.now()}@example.com`

  await askForResetLink(page, email)

  // The API mails after it answers; give a real send time to land.
  await page.waitForTimeout(2_000)
  expect(await messagesTo(email)).toEqual([])
})
