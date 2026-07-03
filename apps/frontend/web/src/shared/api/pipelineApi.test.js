import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getParserOverlay, listFeedHistory, putParserOverlay } from './pipelineApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('pipelineApi — feed history', () => {
  it('lists the full feed history for mining (no limit, dedicated endpoint)', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ messages: [{ id: '1' }, { id: '2' }, { id: '3' }] })
    )

    const body = await listFeedHistory('jwt-token', '7')

    expect(body.messages).toHaveLength(3)
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/feeds/7/messages/history',
      {
        method: 'GET',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })
})

describe('pipelineApi — overlay', () => {
  it('reads the parser overlay', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ overlay: { rejectPhrases: ['x'] } }))
    const body = await getParserOverlay('jwt-token')
    expect(body.overlay.rejectPhrases).toEqual(['x'])
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/parser-overlay', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('writes the parser overlay', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ overlay: { rejectPhrases: ['x'] } }))
    await putParserOverlay('jwt-token', { rejectPhrases: ['x'] })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/parser-overlay', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ overlay: { rejectPhrases: ['x'] } })
    })
  })
})
