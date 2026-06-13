const AUTH_KEY = 'vrs-authenticated-1'

export function isAuthenticated() {
  try {
    return localStorage.getItem(AUTH_KEY) === 'true'
  } catch {
    return false
  }
}

export function rememberAuthenticatedUser() {
  try {
    localStorage.setItem(AUTH_KEY, 'true')
  } catch {
    /* ignore */
  }
}

export function forgetAuthenticatedUser() {
  try {
    localStorage.removeItem(AUTH_KEY)
  } catch {
    /* ignore */
  }
}
