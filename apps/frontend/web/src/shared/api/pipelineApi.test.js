import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getLabelCounts,
  getRules,
  getVerifySamples,
  listMessages,
  recordLabel,
  startDistill,
  streamDistillProgress,
  submitVerify
} from './pipelineApi.js'

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

describe('pipelineApi — distill', () => {
  it('starts a distill job', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'u:7:distill' }, 202))

    const body = await startDistill('jwt-token', '7')

    expect(body.jobId).toBe('u:7:distill')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/distill', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('reads compiled rules', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({
        rules: [{ id: 'r:0', label: 'has verb', detail: '…', match: 94 }]
      })
    )

    const body = await getRules('jwt-token', '7')

    expect(body.rules[0].match).toBe(94)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/rules', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('streams distill progress via the shared helper', () => {
    class FakeEventSource {
      constructor(url) {
        this.url = url
        this.listeners = {}
        FakeEventSource.last = this
      }
      addEventListener(type, listener) {
        this.listeners[type] = listener
      }
      close() {
        this.closed = true
      }
    }
    globalThis.EventSource = FakeEventSource

    streamDistillProgress('jwt-token', '7', {})

    expect(FakeEventSource.last.url).toBe(
      'http://localhost:8000/chats/7/distill/progress?token=jwt-token'
    )
  })
})

describe('pipelineApi — verify', () => {
  it('gets verification samples', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ attempt: 1, samples: [{ id: '1', predicted: 'signal' }] })
    )

    const body = await getVerifySamples('jwt-token', '7')

    expect(body.attempt).toBe(1)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/verify/samples', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('submits verdicts', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ passed: true, misclassified: [] }))
    const verdicts = [{ messageId: '1', verdict: 'correct' }]

    const body = await submitVerify('jwt-token', '7', verdicts)

    expect(body.passed).toBe(true)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ verdicts })
    })
  })
})
