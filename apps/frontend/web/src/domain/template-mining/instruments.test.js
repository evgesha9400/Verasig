import { describe, expect, it } from 'vitest'
import { detectInstruments } from './instruments.js'

function normals(text) {
  return detectInstruments(text).map((entity) => entity.normalized)
}

describe('detectInstruments — direct symbols', () => {
  it('detects a metal symbol', () => {
    expect(normals('XAUUSD BUY NOW')).toContain('XAUUSD')
  })

  it('detects a forex pair by known currency codes', () => {
    expect(normals('Sell EURUSD 1.0860')).toContain('EURUSD')
  })

  it('detects a cross pair like GBPJPY', () => {
    expect(normals('GBPJPY short @ 192.50')).toContain('GBPJPY')
  })

  it('detects an index symbol', () => {
    expect(normals('NAS100 SELL ZONE 19800-19850')).toContain('NAS100')
  })

  it('detects a stock ticker', () => {
    expect(normals('AAPL CALL above 210')).toContain('AAPL')
  })
})

describe('detectInstruments — alias normalization', () => {
  it('maps GOLD to XAUUSD', () => {
    expect(normals('GOLD LONG')).toContain('XAUUSD')
  })

  it('maps XAU to XAUUSD', () => {
    expect(normals('XAU buy')).toContain('XAUUSD')
  })

  it('maps BITCOIN and BTC to BTCUSDT', () => {
    expect(normals('BITCOIN long')).toContain('BTCUSDT')
    expect(normals('BTC long now')).toContain('BTCUSDT')
  })

  it('maps ETHEREUM and ETH to ETHUSDT', () => {
    expect(normals('ETHEREUM short')).toContain('ETHUSDT')
    expect(normals('ETH short hit SL')).toContain('ETHUSDT')
  })

  it('maps NASDAQ and US100 to NAS100', () => {
    expect(normals('NASDAQ buy')).toContain('NAS100')
    expect(normals('US100 buy')).toContain('NAS100')
  })

  it('maps DOW to US30 and DAX to GER40', () => {
    expect(normals('DOW buy now')).toContain('US30')
    expect(normals('DAX sell')).toContain('GER40')
  })

  it('maps SP500 and S&P500 to SPX500', () => {
    expect(normals('SP500 long')).toContain('SPX500')
    expect(normals('S&P500 long')).toContain('SPX500')
  })
})

describe('detectInstruments — crypto pair formats', () => {
  it('detects slash pairs and normalizes to a joined symbol', () => {
    expect(normals('LONG BTC/USDT')).toContain('BTCUSDT')
    expect(normals('SHORT ETH/USDT')).toContain('ETHUSDT')
  })

  it('detects an arbitrary slash pair not in the dictionary', () => {
    expect(normals('SCALP ARB/USDT long 1.124')).toContain('ARBUSDT')
  })
})

describe('detectInstruments — guards', () => {
  it('does not treat an ordinary six-letter word as a forex pair', () => {
    expect(detectInstruments('MARKET orders only please')).toHaveLength(0)
  })

  it('does not match an instrument substring inside a larger word', () => {
    expect(detectInstruments('the solution is golden')).toHaveLength(0)
  })

  it('returns empty for text with no instrument', () => {
    expect(detectInstruments('Good morning team, waiting for NY session')).toHaveLength(
      0
    )
  })

  it('returns entities carrying the raw match and a positive confidence', () => {
    const [entity] = detectInstruments('GOLD LONG')
    expect(entity.raw.toLowerCase()).toBe('gold')
    expect(entity.normalized).toBe('XAUUSD')
    expect(entity.confidence).toBeGreaterThan(0)
  })

  it('deduplicates repeated instruments to one entity per symbol', () => {
    const result = detectInstruments('BTC long, still bullish on BTC')
    expect(result.filter((entity) => entity.normalized === 'BTCUSDT')).toHaveLength(1)
  })
})
