import { describe, expect, it, vi } from 'vitest'
import { weakMemo } from './weakMemo.js'

describe('weakMemo', () => {
  it('caches a legitimately falsy built value instead of rebuilding it', () => {
    const cache = new WeakMap()
    const key = {}
    const build = vi.fn(() => []) // empty array — a real, falsy-adjacent result

    const first = weakMemo(cache, key, build)
    const second = weakMemo(cache, key, build)

    expect(first).toBe(second)
    expect(build).toHaveBeenCalledTimes(1) // built once, then served from cache
  })

  it('does not rebuild when the built value is falsy (0)', () => {
    const cache = new WeakMap()
    const key = {}
    const build = vi.fn(() => 0)

    weakMemo(cache, key, build)
    weakMemo(cache, key, build)

    expect(build).toHaveBeenCalledTimes(1)
  })
})
