import { describe, expect, it } from 'vitest'
import { detectPrices, parseNumber } from './prices.js'

function values(text) {
  return detectPrices(text).map((price) => price.value)
}

describe('parseNumber', () => {
  it('parses a plain integer', () => expect(parseNumber('2320')).toBe(2320))
  it('parses a decimal', () => expect(parseNumber('2320.50')).toBe(2320.5))
  it('parses a forex price', () => expect(parseNumber('1.0865')).toBe(1.0865))
  it('parses thousands separators', () => expect(parseNumber('68,500')).toBe(68500))
  it('expands a k suffix', () => expect(parseNumber('66.5k')).toBe(66500))
  it('expands an m suffix', () => expect(parseNumber('1.2m')).toBe(1200000))
  it('parses a very small crypto price', () =>
    expect(parseNumber('0.0000118')).toBeCloseTo(0.0000118, 12))
})

describe('detectPrices — single levels', () => {
  it('detects a single integer level', () => {
    const [price] = detectPrices('SL 2310')
    expect(price).toMatchObject({ value: 2310, type: 'single' })
  })

  it('detects a decimal level', () => expect(values('entry 2320.50')).toEqual([2320.5]))
  it('detects a forex level', () => expect(values('@ 1.0865')).toEqual([1.0865]))
  it('detects a level written with thousands separators', () =>
    expect(values('entry 68,500')).toEqual([68500]))
})

describe('detectPrices — ranges', () => {
  it('detects a hyphen range as min/max', () => {
    const [price] = detectPrices('Entry 2320-2325')
    expect(price).toMatchObject({ type: 'range', min: 2320, max: 2325 })
  })

  it('detects a spaced hyphen range', () => {
    const [price] = detectPrices('Entry 2320 - 2325')
    expect(price).toMatchObject({ type: 'range', min: 2320, max: 2325 })
  })

  it('detects a "to" range', () => {
    const [price] = detectPrices('Entry 2320 to 2325')
    expect(price).toMatchObject({ type: 'range', min: 2320, max: 2325 })
  })

  it('orders a descending range as min/max', () => {
    const [price] = detectPrices('Entry 64200 - 63750')
    expect(price).toMatchObject({ type: 'range', min: 63750, max: 64200 })
  })
})

describe('detectPrices — lists and labels', () => {
  it('detects a slash-separated target list as separate levels', () => {
    expect(values('Targets 2340 / 2355 / 2370')).toEqual([2340, 2355, 2370])
  })

  it('detects space-separated targets as separate levels', () => {
    expect(values('Targets 19720 19650 19500')).toEqual([19720, 19650, 19500])
  })

  it('does not treat the ordinal in TP1 as a price', () => {
    expect(values('TP1 2340')).toEqual([2340])
  })

  it('detects one level per numbered target line', () => {
    expect(values('TP1 2340\nTP2 2355\nTP3 2370')).toEqual([2340, 2355, 2370])
  })
})

describe('detectPrices — exclusions', () => {
  it('ignores clock times', () =>
    expect(detectPrices('closed at 08:42')).toHaveLength(0))
  it('ignores leverage like 5-10x', () =>
    expect(detectPrices('Leverage 5-10x')).toHaveLength(0))
  it('ignores P&L units like +300 pips', () =>
    expect(detectPrices('running +300 pips')).toHaveLength(0))
  it('ignores point counts like 150 points', () =>
    expect(detectPrices('closed +150 points')).toHaveLength(0))
  it('keeps a price followed by a space and a word starting with x/%', () =>
    expect(values('Entry 2320 Xau zone')).toEqual([2320]))
  it('ignores a clock time that carries seconds', () =>
    expect(detectPrices('filled at 08:42:15')).toHaveLength(0))
  it('skips a separated target ordinal but keeps its value', () =>
    expect(values('TP 1 2340')).toEqual([2340]))
  it('keeps a bare target value that is not an ordinal', () =>
    expect(values('TP 50')).toEqual([50]))
  it('keeps the raw token for display', () => {
    const [price] = detectPrices('SL 2310')
    expect(price.raw).toContain('2310')
  })
})
