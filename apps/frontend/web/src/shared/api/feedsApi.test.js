import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  cancelBackfill,
  createFeed,
  deleteFeed,
  listFeeds,
  startBackfill,
  startDeletionRescan,
  streamBackfillProgress,
  streamDeletionRescanProgress
} from './feedsApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

const feed = {
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
  signalDeletion: false,
  deletedCount: 0
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('feedsApi', () => {
  it('lists feeds with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ feeds: [feed] }))

    const body = await listFeeds('jwt-token')

    expect(body.feeds[0].name).toBe('Pilot Signals')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('creates a feed subscription by tag', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(feed, 201))

    await createFeed('jwt-token', '@pilot')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ tag: '@pilot' })
    })
  })

  it('deletes a feed subscription', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await deleteFeed('jwt-token', '7')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7', {
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

    expect(fetch).toHaveBeenNthCalledWith(1, 'http://localhost:8000/feeds/7/backfill', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ mode: 'resume' })
    })
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/feeds/7/backfill/cancel',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
  })

  it('starts a re-backfill in the requested mode', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))

    await startBackfill('jwt-token', '7', 'full')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/backfill', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ mode: 'full' })
    })
  })

  it('includes the history depth when one is chosen', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))

    await startBackfill('jwt-token', '7', 'full', '6m')

    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/feeds/7/backfill', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ mode: 'full', depth: '6m' })
    })
  })

  it('includes a falsy-but-provided depth (0), only omitting null', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))

    await startBackfill('jwt-token', '7', 'full', 0)

    const sentBody = JSON.parse(fetch.mock.calls[0][1].body)
    expect(sentBody).toEqual({ mode: 'full', depth: 0 })
  })

  it('omits the depth when none is chosen', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:backfill' }, 202))

    await startBackfill('jwt-token', '7', 'resume')

    const sentBody = JSON.parse(fetch.mock.calls[0][1].body)
    expect(sentBody).toEqual({ mode: 'resume' })
  })

  it('starts a deletion rescan job', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'user:7:deletion-rescan' }, 202))

    await startDeletionRescan('jwt-token', '7')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/feeds/7/deletion-rescan',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer jwt-token' }
      }
    )
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
      'http://localhost:8000/feeds/7/backfill/progress?token=jwt-token'
    )
    expect(onProgress).toHaveBeenCalledWith({
      fetched: 5,
      phase: 'Reading channel history…'
    })
    expect(onDone).toHaveBeenCalledWith({ fetched: 12 })
    expect(events[0].closed).toBe(true)
  })

  it('streams deletion rescan progress with the token in the query string', () => {
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

    streamDeletionRescanProgress('jwt-token', '7', {
      onProgress,
      onDone
    })
    events[0].emit('progress', { phase: 'Checking deleted messages...', scanned: 200 })
    events[0].emit('done', { newDeletedSignalCount: 1 })

    expect(events[0].url).toBe(
      'http://localhost:8000/feeds/7/deletion-rescan/progress?token=jwt-token'
    )
    expect(onProgress).toHaveBeenCalledWith({
      phase: 'Checking deleted messages...',
      scanned: 200
    })
    expect(onDone).toHaveBeenCalledWith({ newDeletedSignalCount: 1 })
    expect(events[0].closed).toBe(true)
  })
})
