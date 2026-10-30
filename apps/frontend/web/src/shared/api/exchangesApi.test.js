import { beforeEach, describe, expect, it, vi } from 'vitest'
import { connectExchange, disconnectExchange, listExchanges } from './exchangesApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

const bybit = { id: 'bybit', connected: true, account: 'J7n2…wL' }

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('exchangesApi', () => {
  it('lists exchanges', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ exchanges: [bybit] }))
    const body = await listExchanges('jwt-token')
    expect(body.exchanges).toEqual([bybit])
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/exchanges', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('connects an exchange with its API key pair', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(bybit))
    await connectExchange('jwt-token', 'bybit', { apiKey: 'key', apiSecret: 'secret' })
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/exchanges/bybit/connect',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer jwt-token'
        },
        body: JSON.stringify({ apiKey: 'key', apiSecret: 'secret' })
      }
    )
  })

  it('disconnects an exchange without a body', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ ...bybit, connected: false }))
    await disconnectExchange('jwt-token', 'bybit')
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/exchanges/bybit/disconnect',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })
})
