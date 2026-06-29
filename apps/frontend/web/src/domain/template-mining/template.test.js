import { describe, expect, it } from 'vitest'
import { normalizeTemplate } from './template.js'

function templateOf(text) {
  return normalizeTemplate({ message: { id: 't', text } }).normalizedTemplate
}

describe('normalizeTemplate — matches the specified canonical forms', () => {
  it('normalizes an emoji + range + numbered TP signal', () => {
    const text = '🟢 XAUUSD BUY\nEntry: 2320-2325\nSL: 2312\nTP1: 2340\nTP2: 2355'
    expect(templateOf(text)).toBe(
      '<SIDE_EMOJI> <INSTRUMENT> <SIDE>\nENTRY: <RANGE>\nSL: <PRICE>\nTP1: <PRICE>\nTP2: <PRICE>'
    )
  })

  it('normalizes a market order with a target list', () => {
    const text = 'Gold long now\nStop below 2312\nTargets 2340 / 2355'
    expect(templateOf(text)).toBe(
      '<INSTRUMENT> <SIDE> MARKET\nSTOP BELOW <PRICE>\nTARGETS <PRICE_LIST>'
    )
  })

  it('normalizes an @-entry signal', () => {
    const text = 'SELL EURUSD @ 1.0860\nSL 1.0900\nTP 1.0800'
    expect(templateOf(text)).toBe(
      '<SIDE> <INSTRUMENT> @ <PRICE>\nSL <PRICE>\nTP <PRICE>'
    )
  })

  it('collapses a bare hit-TP update to a structural template', () => {
    expect(templateOf('XAUUSD BUY hit TP1')).toBe('<INSTRUMENT> <SIDE> HIT TP<N>')
  })
})

describe('normalizeTemplate — grouping behaviour', () => {
  it('produces the same template for structurally identical signals', () => {
    const a = normalizeTemplate({
      message: {
        text: '🟢 XAUUSD BUY\nEntry: 2320-2325\nSL: 2312\nTP1: 2340\nTP2: 2355'
      }
    })
    const b = normalizeTemplate({
      message: {
        text: '🔴 BTCUSDT SELL\nEntry: 68200-68400\nSL: 69000\nTP1: 67000\nTP2: 66000'
      }
    })
    expect(a.normalizedTemplate).toBe(b.normalizedTemplate)
    expect(a.templateKey).toBe(b.templateKey)
  })

  it('produces a different template key for a different structure', () => {
    const a = normalizeTemplate({
      message: { text: 'BUY XAUUSD NOW\nSL 2312\nTP 2340' }
    })
    const b = normalizeTemplate({
      message: { text: 'SELL EURUSD @ 1.0860\nSL 1.0900\nTP 1.0800' }
    })
    expect(a.templateKey).not.toBe(b.templateKey)
  })

  it('returns a stable non-empty key for the same input', () => {
    const text = 'BUY XAUUSD NOW\nSL 2312\nTP 2340'
    const first = normalizeTemplate({ message: { text } })
    const second = normalizeTemplate({ message: { text } })
    expect(first.templateKey).toBe(second.templateKey)
    expect(first.templateKey.length).toBeGreaterThan(0)
  })
})
