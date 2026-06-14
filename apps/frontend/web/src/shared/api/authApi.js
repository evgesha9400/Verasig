import { requestJson } from './client.js'

export function login(credentials) {
  return requestJson('/auth/login', {
    method: 'POST',
    body: credentials
  })
}

export function register(account) {
  return requestJson('/auth/register', {
    method: 'POST',
    body: account
  })
}

export function getCurrentUser(token) {
  return requestJson('/auth/me', { token })
}

export function logout(token) {
  return requestJson('/auth/logout', {
    method: 'POST',
    token
  })
}
