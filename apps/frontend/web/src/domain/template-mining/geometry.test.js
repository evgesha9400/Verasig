import { describe, expect, it } from 'vitest'
import { validatePriceGeometry } from './geometry.js'
import { extractSignalFields } from './fields.js'

const buy = (over) => ({
  direction: 'BUY',
  entry: null,
  stopLoss: null,
  takeProfits: [],
  ...over
})
const sell = (over) => ({ ...buy(over), direction: 'SELL' })

describe('validatePriceGeometry — valid structures', () => {
  it('accepts a BUY with stop below and targets above entry', () => {
    const result = validatePriceGeometry(
      buy({
        entry: { type: 'single', price: 2320 },
        stopLoss: 2312,
        takeProfits: [2340, 2355]
      })
    )
    expect(result.isValid).toBe(true)
    expect(result.warnings).toHaveLength(0)
    expect(result.scoreAdjustment).toBeGreaterThan(0)
  })

  it('accepts a SELL with stop above and target below entry range', () => {
    const result = validatePriceGeometry(
      sell({
        entry: { type: 'range', min: 1.086, max: 1.087 },
        stopLoss: 1.09,
        takeProfits: [1.08]
      })
    )
    expect(result.isValid).toBe(true)
  })

  it('accepts a no-entry BUY where stop sits below the targets', () => {
    const result = validatePriceGeometry(
      buy({ stopLoss: 67400, takeProfits: [69000, 70500] })
    )
    expect(result.isValid).toBe(true)
    expect(result.scoreAdjustment).toBeGreaterThan(0)
  })
})

describe('validatePriceGeometry — suspicious structures are downgraded, not rejected', () => {
  it('flags a BUY with stop above entry and target below entry', () => {
    const result = validatePriceGeometry(
      extractSignalFields('BUY XAUUSD 2320\nSL 2340\nTP 2310')
    )
    expect(result.isValid).toBe(false)
    expect(result.warnings.length).toBeGreaterThan(0)
    expect(result.scoreAdjustment).toBeLessThan(0)
  })

  it('flags a no-entry SELL whose stop is below its targets', () => {
    const result = validatePriceGeometry(
      sell({ stopLoss: 100, takeProfits: [110, 120] })
    )
    expect(result.isValid).toBe(false)
  })
})

describe('validatePriceGeometry — insufficient information is skipped', () => {
  it('returns valid with no adjustment when there is nothing to compare', () => {
    const result = validatePriceGeometry(buy({}))
    expect(result.isValid).toBe(true)
    expect(result.scoreAdjustment).toBe(0)
    expect(result.warnings).toHaveLength(0)
  })

  it('skips a market order that has only a stop and no targets', () => {
    const result = validatePriceGeometry(buy({ stopLoss: 2312 }))
    expect(result.isValid).toBe(true)
    expect(result.scoreAdjustment).toBe(0)
  })

  it('accepts a candidate wrapper exposing fields', () => {
    const result = validatePriceGeometry({
      fields: buy({
        entry: { type: 'single', price: 2320 },
        stopLoss: 2312,
        takeProfits: [2340]
      })
    })
    expect(result.isValid).toBe(true)
  })
})
