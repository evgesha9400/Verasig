export const AUTH_TOKEN_KEY = 'vrs-auth-token-1'

const LEGACY_AUTH_KEY = 'vrs-authenticated-1'

export function readAuthToken() {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function rememberAuthToken(token) {
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
    localStorage.removeItem(LEGACY_AUTH_KEY)
  } catch {
    /* ignore */
  }
}

export function forgetAuthToken() {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(LEGACY_AUTH_KEY)
  } catch {
    /* ignore */
  }
}

export function isAuthenticated() {
  return !!readAuthToken()
}

export function rememberAuthenticatedUser(token) {
  if (token) rememberAuthToken(token)
}

export function forgetAuthenticatedUser() {
  forgetAuthToken()
}
