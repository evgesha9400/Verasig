import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  confirmMining,
  getConfirmedMining,
  getMineAudit,
  getMineResult,
  startMine,
  streamMineProgress
} from './mineApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('mineApi', () => {
  it('starts a mine job with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:mine' }, 202))

    const body = await startMine('jwt-token', '7')

    expect(body.jobId).toBe('user:7:mine')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/mining/preview', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('confirms mining with the accepted template keys', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({
        feedStatus: 'verified',
        templatesAccepted: 2,
        signalsExtracted: 5
      })
    )

    const body = await confirmMining('jwt-token', '7', 'review-1', ['tpl_a', 'tpl_b'])

    expect(body.feedStatus).toBe('verified')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/mining/confirm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_a', 'tpl_b']
      })
    })
  })

  it('reads the accepted template keys for a feed (GET, bearer auth)', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ acceptedTemplateKeys: ['tpl_a', 'tpl_b'] })
    )

    const body = await getConfirmedMining('jwt-token', '7')

    expect(body.acceptedTemplateKeys).toEqual(['tpl_a', 'tpl_b'])
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/feeds/7/mining/confirmed',
      {
        method: 'GET',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })

  it('reads the latest current mining review (GET, bearer auth)', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ groups: [{ templateKey: 'tpl_a' }], messages: [{ id: '1' }] })
    )

    const body = await getMineResult('jwt-token', '7')

    expect(body.groups).toEqual([{ templateKey: 'tpl_a' }])
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/mining/result', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('runs the accepted templates over the full history (POST, bearer auth)', async () => {
    const audit = {
      parsedSignals: [],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    fetch.mockResolvedValueOnce(jsonResponse(audit))

    const body = await getMineAudit('jwt-token', '7', 'review-1', ['tpl_a', 'tpl_b'])

    expect(body).toEqual(audit)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/mining/audit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_a', 'tpl_b']
      })
    })
  })

  it('streams mine progress with the token in the query string', () => {
    const events = []
    const onProgress = vi.fn()
    const onDone = vi.fn()

    class FakeEventSource {
      constructor(url) {
        this.url = url
        this.closed = false
        this.listeners = {}
        events.push(this)
      }

      addEventListener(type, listener) {
        this.listeners[type] = listener
      }

      close() {
        this.closed = true
      }

      emit(type, data) {
        this.listeners[type]({ data: JSON.stringify(data) })
      }
    }

    globalThis.EventSource = FakeEventSource

    streamMineProgress('jwt-token', '7', { onProgress, onDone })
    events[0].emit('progress', { stage: 'extracting', count: 42 })
    events[0].emit('done', { groups: [{ template_key: 'tpl_x' }], messages: [] })

    expect(events[0].url).toBe(
      'http://localhost:8000/feeds/7/mining/preview/progress?token=jwt-token'
    )
    expect(onProgress).toHaveBeenCalledWith({ stage: 'extracting', count: 42 })
    expect(onDone).toHaveBeenCalledWith({
      groups: [{ template_key: 'tpl_x' }],
      messages: []
    })
    expect(events[0].closed).toBe(true)
  })
})
