import { beforeEach, describe, expect, it, vi } from 'vitest'
import { linkSignalModifier, listSignals } from './signalsApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('signalsApi', () => {
  it('lists signals with optional filters', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ signals: [{ id: 'sig-1' }], orphanMods: [] })
    )

    const body = await listSignals('jwt-token', {
      feedId: '7',
      status: 'untested'
    })

    expect(body.signals[0].id).toBe('sig-1')
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/signals?feedId=7&status=untested',
      {
        method: 'GET',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })

  it('links an orphan modifier to a signal', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ id: 'sig-1', mods: [{ id: '3' }] }))

    await linkSignalModifier('jwt-token', 'sig-1', '3')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/signals/sig-1/link-mod', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ modId: '3' })
    })
  })
})
