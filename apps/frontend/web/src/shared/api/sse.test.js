import { describe, expect, it, vi } from 'vitest'
import { streamJobProgress } from './sse.js'

class FakeEventSource {
  static CONNECTING = 0
  static CLOSED = 2
  constructor(url) {
    this.url = url
    this.closed = false
    this.readyState = FakeEventSource.CONNECTING
    this.listeners = {}
    FakeEventSource.last = this
  }
  addEventListener(type, listener) {
    this.listeners[type] = listener
  }
  close() {
    this.closed = true
    this.readyState = FakeEventSource.CLOSED
  }
  emit(type, data) {
    this.listeners[type]({
      data: data === undefined ? undefined : JSON.stringify(data)
    })
  }
}

describe('streamJobProgress', () => {
  it('builds the URL with the token query param and wires events', () => {
    globalThis.EventSource = FakeEventSource
    const onProgress = vi.fn()
    const onDone = vi.fn()

    streamJobProgress('jwt-token', '/feeds/7/mine/progress', { onProgress, onDone })
    const source = FakeEventSource.last

    expect(source.url).toBe(
      'http://localhost:8000/feeds/7/mine/progress?token=jwt-token'
    )
    source.emit('progress', { phase: 'Detecting signal templates', step: 1 })
    source.emit('done', { groups: 3 })

    expect(onProgress).toHaveBeenCalledWith({
      phase: 'Detecting signal templates',
      step: 1
    })
    expect(onDone).toHaveBeenCalledWith({ groups: 3 })
    expect(source.closed).toBe(true)
  })

  it('closes and reports on a server-sent error event (carrying data)', () => {
    globalThis.EventSource = FakeEventSource
    const onError = vi.fn()

    streamJobProgress('jwt-token', '/feeds/7/mine/progress', { onError })
    const source = FakeEventSource.last
    source.emit('error', { message: 'Backfill failed.' })

    expect(onError).toHaveBeenCalledWith({ message: 'Backfill failed.' })
    expect(source.closed).toBe(true)
  })

  it('ignores a transient error and lets the stream auto-reconnect', () => {
    globalThis.EventSource = FakeEventSource
    const onError = vi.fn()

    streamJobProgress('jwt-token', '/feeds/7/mine/progress', { onError })
    const source = FakeEventSource.last
    // native EventSource error: no data, still connecting (about to retry)
    source.emit('error', undefined)

    expect(onError).not.toHaveBeenCalled()
    expect(source.closed).toBe(false)
  })
})
