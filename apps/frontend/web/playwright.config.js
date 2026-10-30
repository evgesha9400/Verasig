import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { config as loadEnv } from 'dotenv'
import { defineConfig, devices } from '@playwright/test'

import { AUTH_STATE_PATH } from './e2e/auth-state-path.js'
import { APP_ORIGIN } from './e2e/urls.js'

const HERE = path.dirname(fileURLToPath(import.meta.url))

// Local, git-ignored settings (see e2e/.env.example): login creds for the
// real-backend session and E2E_STRIPE_WEBHOOK_SECRET for checkout.spec.js.
loadEnv({ path: path.join(HERE, 'e2e', '.env') })

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: APP_ORIGIN,
    trace: 'on-first-retry'
  },
  projects: [
    // 1) Log in once via the API and persist the session to a storage-state file.
    { name: 'setup', testMatch: /auth\.setup\.js/ },
    // 2) Real tests, started already authenticated from that storage state.
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: AUTH_STATE_PATH },
      dependencies: ['setup']
    }
  ],
  // Reuse a running dev server (e.g. `docker compose up`); otherwise start one.
  // The backend (:8000) must be up separately for login + data to resolve.
  webServer: {
    command: 'npm run dev',
    url: APP_ORIGIN,
    reuseExistingServer: true,
    timeout: 120_000
  }
})
