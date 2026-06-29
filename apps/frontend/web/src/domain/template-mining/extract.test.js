import { describe, expect, it } from 'vitest'
import { attemptExtractSignal } from './extract.js'

describe('attemptExtractSignal — the parser is the classifier', () => {
  it('returns null when there is no instrument and no direction', () => {
    expect(
      attemptExtractSignal({
        id: '1',
        text: 'Good morning team, waiting for NY session'
      })
    ).toBeNull()
  })

  it('returns null when an instrument has no direction', () => {
    expect(
      attemptExtractSignal({
        id: '1',
        text: 'XAUUSD analysis: price may reject from 2330'
      })
    ).toBeNull()
  })

  it('accepts a raw string and wraps it into a candidate', () => {
    const candidate = attemptExtractSignal('BUY XAUUSD NOW\nSL 2312')
    expect(candidate).not.toBeNull()
    expect(candidate.message.text).toContain('XAUUSD')
  })
})

describe('attemptExtractSignal — full new signal', () => {
  const candidate = attemptExtractSignal({
    id: 'm1',
    text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355'
  })

  it('extracts the structured fields', () => {
    expect(candidate.fields).toMatchObject({
      instrument: 'XAUUSD',
      direction: 'BUY',
      orderType: 'market',
      entry: null,
      stopLoss: 2312,
      takeProfits: [2340, 2355]
    })
  })

  it('classifies intent as new_signal with high confidence and no rejections', () => {
    expect(candidate.intent).toBe('new_signal')
    expect(candidate.confidence).toBeGreaterThan(0.7)
    expect(candidate.rejectionReasons).toHaveLength(0)
  })

  it('carries a normalized template and key', () => {
    expect(candidate.templateKey).toMatch(/^tpl_/)
    expect(candidate.normalizedTemplate).toContain('<INSTRUMENT>')
  })
})

describe('attemptExtractSignal — range signal', () => {
  it('parses a EURUSD range sell', () => {
    const candidate = attemptExtractSignal({
      id: 'm2',
      text: 'Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800'
    })
    expect(candidate.fields.orderType).toBe('range')
    expect(candidate.fields.entry).toMatchObject({
      type: 'range',
      min: 1.086,
      max: 1.087
    })
    expect(candidate.intent).toBe('new_signal')
  })
})

describe('attemptExtractSignal — only new signals are candidates', () => {
  it('returns null for a result (hit TP) — not a new signal', () => {
    expect(attemptExtractSignal({ id: 'm3', text: 'XAUUSD BUY hit TP1' })).toBeNull()
  })

  it('returns null for an update (stop move) — not a new signal', () => {
    expect(
      attemptExtractSignal({ id: 'm4', text: 'Move SL to BE on gold buy' })
    ).toBeNull()
  })

  it('returns null for directional commentary with no structure', () => {
    expect(
      attemptExtractSignal({
        id: 'm6',
        text: 'The whale stays long on BTC across every exchange while volume keeps climbing steadily'
      })
    ).toBeNull()
  })
})

describe('attemptExtractSignal — suspicious geometry is flagged, not dropped', () => {
  it('flags reversed stop/target placement', () => {
    const candidate = attemptExtractSignal({
      id: 'm5',
      text: 'BUY XAUUSD 2320\nSL 2340\nTP 2310'
    })
    expect(candidate).not.toBeNull()
    expect(
      candidate.rejectionReasons.some((reason) => /stop|target|entry/i.test(reason))
    ).toBe(true)
  })
})
