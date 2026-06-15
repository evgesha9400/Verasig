import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getLabelCounts, listMessages, recordLabel } from './pipelineApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('pipelineApi — label', () => {
  it('lists messages with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ messages: [{ id: '1' }] }))

    const body = await listMessages('jwt-token', '7')

    expect(body.messages[0].id).toBe('1')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/messages', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('records a label as an idempotent upsert', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await recordLabel('jwt-token', '7', '42', 'signal')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/chats/7/messages/42/label',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer jwt-token'
        },
        body: JSON.stringify({ label: 'signal' })
      }
    )
  })

  it('reads label counts', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ signalCount: 3, noiseCount: 2, modifierCount: 0, total: 5 })
    )

    const counts = await getLabelCounts('jwt-token', '7')

    expect(counts.signalCount).toBe(3)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/labels', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })
})
