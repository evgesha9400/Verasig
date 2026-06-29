import { describe, expect, it } from 'vitest'
import { detectDirections } from './directions.js'

function sides(text) {
  return detectDirections(text).map((entity) => entity.normalized)
}

describe('detectDirections — buy words', () => {
  it('detects buy', () => expect(sides('XAUUSD BUY NOW')).toContain('BUY'))
  it('detects long', () => expect(sides('GOLD LONG')).toContain('BUY'))
  it('detects bullish', () => expect(sides('looking bullish here')).toContain('BUY'))
  it('detects call', () => expect(sides('AAPL CALL above 210')).toContain('BUY'))
})

describe('detectDirections — sell words', () => {
  it('detects sell', () => expect(sides('Sell EURUSD 1.0860')).toContain('SELL'))
  it('detects short', () => expect(sides('ETH short hit SL')).toContain('SELL'))
  it('detects bearish', () => expect(sides('bearish below support')).toContain('SELL'))
  it('detects put', () => expect(sides('TSLA PUT 180')).toContain('SELL'))
})

describe('detectDirections — case and absence', () => {
  it('is case-insensitive', () => expect(sides('Buy gold')).toContain('BUY'))
  it('returns nothing when no direction word or emoji exists', () => {
    expect(detectDirections('Good morning team, waiting for NY session')).toHaveLength(
      0
    )
  })
})

describe('detectDirections — emojis are lower confidence', () => {
  it('reads a green circle as BUY', () => {
    expect(sides('🟢 GOLD entry 2320')).toContain('BUY')
  })

  it('reads a red circle as SELL', () => {
    expect(sides('🔴 EURUSD entry 1.0860')).toContain('SELL')
  })

  it('reads arrows as direction', () => {
    expect(sides('XAUUSD ⬆️ 2320')).toContain('BUY')
    expect(sides('XAUUSD ⬇️ 2320')).toContain('SELL')
  })

  it('scores an emoji-only direction below a word direction', () => {
    const emoji = detectDirections('🟢')[0]
    const word = detectDirections('buy')[0]
    expect(emoji.confidence).toBeLessThan(word.confidence)
  })

  it('carries the raw token and span', () => {
    const [entity] = detectDirections('GOLD LONG')
    expect(entity.raw.toLowerCase()).toBe('long')
    expect(entity.normalized).toBe('BUY')
    expect(entity.start).toBeGreaterThanOrEqual(0)
  })
})
