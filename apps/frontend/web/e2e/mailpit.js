import { expect } from '@playwright/test'

// Mailpit's HTTP API (https://mailpit.axllent.org/docs/api-v1/): CI and local
// dev send all app mail to Mailpit, and the specs read it back here.
export const MAIL_API_URL = process.env.E2E_MAIL_API_URL

async function getJson(path) {
  const response = await fetch(`${MAIL_API_URL}${path}`)
  expect(
    response.ok,
    `GET ${MAIL_API_URL}${path} failed (HTTP ${response.status})`
  ).toBe(true)
  return response.json()
}

export async function messagesTo(address) {
  const query = encodeURIComponent(`to:"${address}"`)
  const { messages } = await getJson(`/api/v1/search?query=${query}`)
  return messages
}

export async function readMessage(id) {
  return getJson(`/api/v1/message/${id}`)
}

// Waits for the first message to `address` and returns its full body.
export async function waitForMessageTo(address) {
  let found
  await expect
    .poll(async () => (found = (await messagesTo(address))[0]), {
      message: `no email to ${address} reached Mailpit`,
      timeout: 15_000
    })
    .toBeTruthy()
  return readMessage(found.ID)
}
