import { get, post } from './client.js'

export function login(credentials) {
  return post('/auth/login', null, credentials)
}

export function register(account) {
  return post('/auth/register', null, account)
}

export function getCurrentUser(token) {
  return get('/auth/me', token)
}

export function logout(token) {
  return post('/auth/logout', token)
}
