import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cancelEmailChange, changeEmail, updateProfile } from './userApi.js'

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
  plan: 'trader',
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
})
