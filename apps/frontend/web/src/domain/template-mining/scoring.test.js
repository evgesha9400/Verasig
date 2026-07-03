import { describe, expect, it } from 'vitest'
import { scoreCandidate } from './scoring.js'
import { extractSignalFields } from './fields.js'
import { detectDirections } from './directions.js'

function candidateOf(text) {
  return {
    message: { id: 't', text },
    fields: extractSignalFields(text),
    directions: detectDirections(text)
  }
}

describe('scoreCandidate — bounds', () => {
  it('always returns a confidence between 0 and 1', () => {
    const texts = [
      'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355',
      'Move SL to BE on gold buy',
      'gm everyone',
      'XAUUSD BUY hit TP1 ✅'
    ]
    for (const text of texts) {
      const score = scoreCandidate(candidateOf(text))
      expect(score).toBeGreaterThanOrEqual(0)
      expect(score).toBeLessThanOrEqual(1)
    }
  })
})

describe('scoreCandidate — ranking', () => {
  it('scores a complete new signal highly', () => {
    expect(
      scoreCandidate(candidateOf('XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355'))
    ).toBeGreaterThan(0.7)
  })

  it('scores an update below a complete new signal', () => {
    const signal = scoreCandidate(candidateOf('XAUUSD BUY NOW\nSL 2312\nTP 2340'))
    const update = scoreCandidate(candidateOf('Move SL to BE on gold buy'))
    expect(update).toBeLessThan(signal)
    expect(update).toBeLessThan(0.4)
  })

  it('scores a TP-hit result low', () => {
    expect(scoreCandidate(candidateOf('XAUUSD BUY hit TP1 ✅'))).toBeLessThan(0.4)
  })

  it('ranks a complete signal above a bare directional call', () => {
    const full = scoreCandidate(
      candidateOf('XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355')
    )
    const bare = scoreCandidate(candidateOf('BTC long'))
    expect(full).toBeGreaterThan(bare)
  })

  it('penalizes an emoji-only direction relative to a worded one', () => {
    const emojiOnly = scoreCandidate(
      candidateOf('🟢 XAUUSD\nEntry 2320\nSL 2312\nTP 2340')
    )
    const worded = scoreCandidate(
      candidateOf('BUY XAUUSD\nEntry 2320\nSL 2312\nTP 2340')
    )
    expect(emojiOnly).toBeLessThan(worded)
  })
})
