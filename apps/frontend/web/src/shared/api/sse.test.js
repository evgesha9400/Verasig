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

    streamJobProgress('jwt-token', '/chats/7/distill/progress', { onProgress, onDone })
    const source = FakeEventSource.last

    expect(source.url).toBe(
      'http://localhost:8000/chats/7/distill/progress?token=jwt-token'
    )
    source.emit('progress', { phase: 'Reading your labelled signals' })
    source.emit('done', { rules: 5 })

    expect(onProgress).toHaveBeenCalledWith({ phase: 'Reading your labelled signals' })
    expect(onDone).toHaveBeenCalledWith({ rules: 5 })
    expect(source.closed).toBe(true)
  })

  it('closes and reports on an error event', () => {
    globalThis.EventSource = FakeEventSource
    const onError = vi.fn()

    streamJobProgress('jwt-token', '/chats/7/distill/progress', { onError })
    const source = FakeEventSource.last
    source.emit('error', undefined)

    expect(onError).toHaveBeenCalledWith({})
    expect(source.closed).toBe(true)
  })
})
