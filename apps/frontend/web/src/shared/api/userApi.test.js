import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  cancelEmailChange,
  cancelSubscription,
  changeEmail,
  changeSubscription,
  requestPasswordReset,
  resumeSubscription,
  updateProfile
} from './userApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

const user = {
  firstName: 'Grace',
  lastName: 'Hopper',
  email: 'grace@example.com',
  plan: 'operator',
  pendingEmail: null,
  cancelAt: null
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('userApi', () => {
  it('updates profile names with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(user))

    await updateProfile('jwt-token', {
      firstName: 'Grace',
      lastName: 'Hopper'
    })

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        firstName: 'Grace',
        lastName: 'Hopper'
      })
    })
  })

  it('requests an email change', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({
        ...user,
        email: 'ada@example.com',
        pendingEmail: 'next@example.com'
      })
    )

    const body = await changeEmail('jwt-token', 'next@example.com')

    expect(body.pendingEmail).toBe('next@example.com')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user/email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ email: 'next@example.com' })
    })
  })

  it('cancels a pending email change without a body', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(user))

    const body = await cancelEmailChange('jwt-token')

    expect(body.pendingEmail).toBeNull()
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user/email/cancel', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('requests a password reset without a body', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 202 }))

    await requestPasswordReset('jwt-token')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/user/password/reset-request',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })

  it('changes subscription plan', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ ...user, plan: 'desk' }))

    await changeSubscription('jwt-token', 'desk')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/user/subscription/change',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer jwt-token'
        },
        body: JSON.stringify({ plan: 'desk' })
      }
    )
  })

  it('cancels and resumes subscription', async () => {
    fetch
      .mockResolvedValueOnce(
        jsonResponse({ ...user, cancelAt: '2026-07-08T00:00:00Z' })
      )
      .mockResolvedValueOnce(jsonResponse({ ...user, cancelAt: null }))

    await cancelSubscription('jwt-token')
    await resumeSubscription('jwt-token')

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/user/subscription/cancel',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/user/subscription/resume',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })
})
