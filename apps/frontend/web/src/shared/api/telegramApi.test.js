import { beforeEach, describe, expect, it, vi } from 'vitest'
import { connectTelegram, getTelegramStatus, verifyTelegram } from './telegramApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('telegramApi', () => {
  it('loads Telegram connection status', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ connected: true, phone: '+44 •••• 8821' })
    )

    const status = await getTelegramStatus('jwt-token')

    expect(status.connected).toBe(true)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/telegram/status', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('starts Telegram connection with credentials', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 202 }))

    await connectTelegram('jwt-token', {
      apiId: 123,
      apiHash: 'api-secret',
      phone: '+441234568821'
    })

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/telegram/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        apiId: 123,
        apiHash: 'api-secret',
        phone: '+441234568821'
      })
    })
  })

  it('verifies a Telegram login code', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ connected: true }))

    await verifyTelegram('jwt-token', '12345')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/telegram/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ code: '12345' })
    })
  })

  it('verifies a Telegram login code with optional two-factor password', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ connected: true }))

    await verifyTelegram('jwt-token', '12345', 'two-factor-password')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/telegram/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        code: '12345',
        password: 'two-factor-password'
      })
    })
  })
})
