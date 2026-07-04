import path from 'node:path'
import { fileURLToPath } from 'node:url'

// Single source of truth for the git-ignored Playwright storage-state file,
// shared by playwright.config.js (reads it) and auth.setup.js (writes it).
export const AUTH_STATE_PATH = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '.auth',
  'state.json'
)
