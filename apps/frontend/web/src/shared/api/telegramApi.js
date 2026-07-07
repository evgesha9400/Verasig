import { get, post } from './client.js'

export function getTelegramStatus(token) {
  return get('/telegram/status', token)
}

export function connectTelegram(token, credentials) {
  return post('/telegram/connect', token, credentials)
}

export function verifyTelegram(token, code, password) {
  return post('/telegram/verify', token, { code, password })
}
