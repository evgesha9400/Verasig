import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client.js'
import { getCurrentUser, login, logout, register } from './authApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('authApi', () => {
  it('logs in with the backend auth contract', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({
        token: 'jwt-token',
        user: {
          firstName: 'Ada',
          lastName: 'Lovelace',
          email: 'ada@example.com',
          plan: 'free',
          pendingEmail: null,
          cancelAt: null
        }
      })
    )

    const body = await login({
      email: 'ADA@example.com',
      password: 'correct horse battery staple'
    })

    expect(body.token).toBe('jwt-token')
    expect(body.user.email).toBe('ada@example.com')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'ADA@example.com',
        password: 'correct horse battery staple'
      })
    })
  })

  it('registers with first and last name fields expected by the backend', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse(
        {
          token: 'new-token',
          user: {
            firstName: 'Mara',
            lastName: 'Voss',
            email: 'mara@example.com',
            plan: 'free',
            pendingEmail: null,
            cancelAt: null
          }
        },
        201
      )
    )

    const body = await register({
      firstName: 'Mara',
      lastName: 'Voss',
      email: 'mara@example.com',
      password: 'verasig-demo-2026'
    })

    expect(body.user.firstName).toBe('Mara')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        firstName: 'Mara',
        lastName: 'Voss',
        email: 'mara@example.com',
        password: 'verasig-demo-2026'
      })
    })
  })

  it('loads the current user with a bearer token', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({
        firstName: 'Ada',
        lastName: 'Lovelace',
        email: 'ada@example.com',
        plan: 'free',
        pendingEmail: null,
        cancelAt: null
      })
    )

    await getCurrentUser('jwt-token')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/auth/me', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('logs out with the active bearer token', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await logout('jwt-token')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/auth/logout', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('throws backend error envelopes as ApiError values', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse(
        {
          error: {
            code: 'AUTH_INVALID_CREDENTIALS',
            message: 'Invalid email or password'
          }
        },
        401
      )
    )

    const result = login({ email: 'ada@example.com', password: 'wrong password' })

    await expect(result).rejects.toBeInstanceOf(ApiError)
    await expect(result).rejects.toMatchObject({
      status: 401,
      code: 'AUTH_INVALID_CREDENTIALS',
      message: 'Invalid email or password'
    })
  })

  it('throws FastAPI validation details as field-level ApiError values', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: [
            {
              type: 'string_too_short',
              loc: ['body', 'password'],
              msg: 'String should have at least 8 characters'
            }
          ]
        },
        422
      )
    )

    const result = register({
      firstName: 'Mara',
      lastName: 'Voss',
      email: 'mara@example.com',
      password: 'short'
    })

    await expect(result).rejects.toBeInstanceOf(ApiError)
    await expect(result).rejects.toMatchObject({
      status: 422,
      code: 'HTTP_422',
      message: 'Password: String should have at least 8 characters'
    })
  })
})
