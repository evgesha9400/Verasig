import { describe, expect, it, vi } from 'vitest'
import { streamJobProgress } from './sse.js'

class FakeEventSource {
  constructor(url) {
    this.url = url
    this.closed = false
    this.listeners = {}
    FakeEventSource.last = this
  }
  addEventListener(type, listener) {
    this.listeners[type] = listener
  }
  close() {
    this.closed = true
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

  it('closes and reports on an error event', () => {
    globalThis.EventSource = FakeEventSource
    const onError = vi.fn()

    streamJobProgress('jwt-token', '/feeds/7/mine/progress', { onError })
    const source = FakeEventSource.last
    source.emit('error', undefined)

    expect(onError).toHaveBeenCalledWith({})
    expect(source.closed).toBe(true)
  })
})
