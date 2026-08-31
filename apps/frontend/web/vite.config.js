import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configDefaults } from 'vitest/config'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  ...(mode === 'test' ? { esbuild: { jsx: 'automatic' } } : {}),
  server: { port: 5173 },
  preview: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    // Playwright specs under e2e/ run via `npm run e2e`, not vitest.
    exclude: [...configDefaults.exclude, 'e2e/**']
  }
}))
