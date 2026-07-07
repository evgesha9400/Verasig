import { patch, post } from './client.js'

export function updateProfile(token, profile) {
  return patch('/user', token, profile)
}

export function changeEmail(token, email) {
  return post('/user/email', token, { email })
}

export function requestPasswordReset(token) {
  return post('/user/password/reset-request', token)
}

export function changeSubscription(token, plan) {
  return post('/user/subscription/change', token, { plan })
}

export function cancelSubscription(token) {
  return post('/user/subscription/cancel', token)
}

export function resumeSubscription(token) {
  return post('/user/subscription/resume', token)
}
