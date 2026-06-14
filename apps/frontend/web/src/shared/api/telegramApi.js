import { requestJson } from './client.js'

export function getTelegramStatus(token) {
  return requestJson('/telegram/status', { token })
}

export function connectTelegram(token, credentials) {
  return requestJson('/telegram/connect', {
    method: 'POST',
    token,
    body: credentials
  })
}

export function verifyTelegram(token, code, password) {
  return requestJson('/telegram/verify', {
    method: 'POST',
    token,
    body: { code, password }
  })
}
