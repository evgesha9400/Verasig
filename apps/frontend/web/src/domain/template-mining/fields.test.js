import { describe, expect, it } from 'vitest'
import { extractSignalFields } from './fields.js'

describe('extractSignalFields — instrument & direction', () => {
  it('normalizes instrument and preserves the raw alias', () => {
    const fields = extractSignalFields('GOLD long now')
    expect(fields.instrument).toBe('XAUUSD')
    expect(fields.instrumentRaw.toLowerCase()).toBe('gold')
    expect(fields.direction).toBe('BUY')
  })

  it('chooses a word direction over an ambiguous emoji', () => {
    expect(extractSignalFields('🔴 EURUSD sell 1.0860').direction).toBe('SELL')
  })
})

describe('extractSignalFields — entry & order type', () => {
  it('treats "now" as a market order with no entry', () => {
    const fields = extractSignalFields('BUY XAUUSD NOW')
    expect(fields.entry).toBeNull()
    expect(fields.orderType).toBe('market')
  })

  it('reads "@ price" as a single limit entry', () => {
    const fields = extractSignalFields('BUY XAUUSD @ 2320')
    expect(fields.entry).toMatchObject({ type: 'single', price: 2320 })
    expect(fields.orderType).toBe('limit')
  })

  it('reads a labelled entry range', () => {
    const fields = extractSignalFields('XAUUSD BUY\nEntry: 2320-2325')
    expect(fields.entry).toMatchObject({ type: 'range', min: 2320, max: 2325 })
    expect(fields.orderType).toBe('range')
  })

  it('reads a "zone" entry range', () => {
    const fields = extractSignalFields('NAS100 SELL ZONE 19800-19850')
    expect(fields.instrument).toBe('NAS100')
    expect(fields.direction).toBe('SELL')
    expect(fields.entry).toMatchObject({ type: 'range', min: 19800, max: 19850 })
    expect(fields.orderType).toBe('range')
  })

  it('reads an inline header price as the entry', () => {
    const fields = extractSignalFields('SHORT DOGE/USDT 0.1620')
    expect(fields.entry).toMatchObject({ type: 'single', price: 0.162 })
  })

  it('assumes a market order when no entry is present', () => {
    const fields = extractSignalFields('BTC LONG\nSL 67400\nTP 69000')
    expect(fields.entry).toBeNull()
    expect(fields.orderType).toBe('market')
  })
})

describe('extractSignalFields — stop loss', () => {
  it('reads an SL label', () => {
    expect(extractSignalFields('XAUUSD BUY\nSL 2310').stopLoss).toBe(2310)
  })

  it('reads a "stop below" label', () => {
    expect(extractSignalFields('GOLD long\nStop below 2310').stopLoss).toBe(2310)
  })

  it('reads an "invalidation" label', () => {
    expect(extractSignalFields('NAS100 sell\nInvalidation 19920').stopLoss).toBe(19920)
  })

  it('does not read a risk percentage as a stop', () => {
    expect(
      extractSignalFields('LONG SOL/USDT 148.5\nRisk 2% of book').stopLoss
    ).toBeNull()
  })
})

describe('extractSignalFields — take profits', () => {
  it('reads a single TP', () => {
    expect(extractSignalFields('XAUUSD BUY\nTP 2340').takeProfits).toEqual([2340])
  })

  it('accumulates numbered TP lines in order', () => {
    const fields = extractSignalFields('XAUUSD BUY\nTP1 2340\nTP2 2355\nTP3 2370')
    expect(fields.takeProfits).toEqual([2340, 2355, 2370])
  })

  it('reads a target list on one line', () => {
    const fields = extractSignalFields('GOLD long\nTargets 2340 / 2355 / 2370')
    expect(fields.takeProfits).toEqual([2340, 2355, 2370])
  })
})

describe('extractSignalFields — full signals', () => {
  it('parses a market XAU signal with two TP lines', () => {
    const fields = extractSignalFields('XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355')
    expect(fields).toMatchObject({
      instrument: 'XAUUSD',
      direction: 'BUY',
      orderType: 'market',
      entry: null,
      stopLoss: 2312,
      takeProfits: [2340, 2355]
    })
  })

  it('parses a EURUSD range sell signal', () => {
    const fields = extractSignalFields(
      'Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800'
    )
    expect(fields).toMatchObject({
      instrument: 'EURUSD',
      direction: 'SELL',
      orderType: 'range',
      stopLoss: 1.09,
      takeProfits: [1.08]
    })
    expect(fields.entry).toMatchObject({ type: 'range', min: 1.086, max: 1.087 })
  })

  it('accepts a ChatMessage object as input', () => {
    const fields = extractSignalFields({ id: 'x', text: 'BUY XAUUSD NOW\nSL 2312' })
    expect(fields.instrument).toBe('XAUUSD')
    expect(fields.stopLoss).toBe(2312)
  })
})
