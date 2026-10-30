// Where the specs reach the web app and the API (CI points both at the site).
export const API_URL =
  process.env.E2E_API_URL || process.env.VITE_VERASIG_API_URL || 'http://localhost:8000'
export const APP_ORIGIN = process.env.E2E_BASE_URL || 'http://localhost:5173'
