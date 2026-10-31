import { patch, post } from './client.js'

export function updateProfile(token, profile) {
  return patch('/user', token, profile)
}

export function changeEmail(token, email) {
  return post('/user/email', token, { email })
}

export function cancelEmailChange(token) {
  return post('/user/email/cancel', token)
}
