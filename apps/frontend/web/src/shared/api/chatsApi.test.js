import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  cancelBackfill,
  createChat,
  deleteChat,
  listChats,
  startBackfill,
  streamBackfillProgress
} from './chatsApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

const chat = {
  id: '7',
  name: 'Pilot Signals',
  tag: '@pilot',
  subscribers: 1234,
  initials: 'PS',
  tint: 'var(--viz-1)',
  status: 'new',
  fetched: 0,
  lastDate: null,
  score: null,
  winRate: null,
  pnl: null,
  hasRisk: false,
  historyGaps: false,
  signalDeletion: false
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('chatsApi', () => {
  it('lists chats with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ chats: [chat] }))

    const body = await listChats('jwt-token')

    expect(body.chats[0].name).toBe('Pilot Signals')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('creates a chat subscription by tag', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(chat, 201))

    await createChat('jwt-token', '@pilot')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ tag: '@pilot' })
    })
  })

  it('deletes a chat subscription', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await deleteChat('jwt-token', '7')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7', {
      method: 'DELETE',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('starts and cancels a backfill job', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await startBackfill('jwt-token', '7')
    await cancelBackfill('jwt-token', '7')

    expect(fetch).toHaveBeenNthCalledWith(1, 'http://localhost:8000/chats/7/backfill', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ mode: 'resume' })
    })
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/chats/7/backfill/cancel',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })

  it('starts a re-backfill in the requested mode', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))

    await startBackfill('jwt-token', '7', 'full')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/backfill', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ mode: 'full' })
    })
  })

  it('streams backfill progress with the token in the query string', () => {
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

    streamBackfillProgress('jwt-token', '7', {
      onProgress,
      onDone
    })
    events[0].emit('progress', { fetched: 5, phase: 'Reading channel history…' })
    events[0].emit('done', { fetched: 12 })

    expect(events[0].url).toBe(
      'http://localhost:8000/chats/7/backfill/progress?token=jwt-token'
    )
    expect(onProgress).toHaveBeenCalledWith({
      fetched: 5,
      phase: 'Reading channel history…'
    })
    expect(onDone).toHaveBeenCalledWith({ fetched: 12 })
    expect(events[0].closed).toBe(true)
  })
})
