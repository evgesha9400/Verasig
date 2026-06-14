import { requestJson } from './client.js'

export function updateProfile(token, profile) {
  return requestJson('/user', {
    method: 'PATCH',
    token,
    body: profile
  })
}

export function changeEmail(token, email) {
  return requestJson('/user/email', {
    method: 'POST',
    token,
    body: { email }
  })
}

export function requestPasswordReset(token) {
  return requestJson('/user/password/reset-request', {
    method: 'POST',
    token
  })
}

export function changeSubscription(token, plan) {
  return requestJson('/user/subscription/change', {
    method: 'POST',
    token,
    body: { plan }
  })
}

export function cancelSubscription(token) {
  return requestJson('/user/subscription/cancel', {
    method: 'POST',
    token
  })
}

export function resumeSubscription(token) {
  return requestJson('/user/subscription/resume', {
    method: 'POST',
    token
  })
}
