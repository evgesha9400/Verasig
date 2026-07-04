import fs from 'node:fs'
import path from 'node:path'

import { expect, request, test as setup } from '@playwright/test'

import { AUTH_STATE_PATH } from './auth-state-path.js'

// The web app stores its session as a bare JWT under this localStorage key
// (see apps/frontend/web/src/app/session.js) and sends it as a Bearer header.
const TOKEN_KEY = 'vrs-auth-token-1'

const API_URL =
  process.env.E2E_API_URL || process.env.VITE_VERASIG_API_URL || 'http://localhost:8000'
const APP_ORIGIN = process.env.E2E_BASE_URL || 'http://localhost:5173'

setup('authenticate via API login', async () => {
  const { email, password } = readCredentials()
  const token = await logInForToken(email, password)
  writeStorageState(token)
})

function readCredentials() {
  const email = process.env.E2E_EMAIL
  const password = process.env.E2E_PASSWORD
  expect(
    Boolean(email && password),
    'Missing creds: copy apps/frontend/web/e2e/.env.example to e2e/.env and set E2E_EMAIL / E2E_PASSWORD.'
  ).toBeTruthy()
  return { email, password }
}

async function logInForToken(email, password) {
  const api = await request.newContext()
  const response = await api.post(`${API_URL}/auth/login`, {
    data: { email, password }
  })
  expect(
    response.ok(),
    `POST ${API_URL}/auth/login failed (HTTP ${response.status()}). Is the backend up (docker compose up) and are the creds correct?`
  ).toBeTruthy()
  const { token } = await response.json()
  expect(token, 'Login succeeded but the response carried no token.').toBeTruthy()
  await api.dispose()
  return token
}

function writeStorageState(token) {
  const state = {
    cookies: [],
    origins: [{ origin: APP_ORIGIN, localStorage: [{ name: TOKEN_KEY, value: token }] }]
  }
  fs.mkdirSync(path.dirname(AUTH_STATE_PATH), { recursive: true })
  fs.writeFileSync(AUTH_STATE_PATH, JSON.stringify(state, null, 2))
}
