import { describe, expect, it } from 'vitest'
import { mineTemplateGroups } from './mining.js'

const SIGNALS = [
  { id: 's1', date: '2026-06-01', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355' },
  { id: 's2', date: '2026-06-02', text: 'XAUUSD BUY NOW\nSL 2305\nTP 2330\nTP 2350' },
  { id: 's3', date: '2026-06-03', text: 'XAUUSD BUY NOW\nSL 2300\nTP 2325\nTP 2345' }
]
const RESULTS = [
  { id: 'r1', date: '2026-06-01', text: 'XAUUSD BUY hit TP1' },
  { id: 'r2', date: '2026-06-02', text: 'EURUSD SELL hit TP1' }
]
const NOISE = [
  { id: 'n1', text: 'gm team, choppy open' },
  { id: 'n2', text: 'join our VIP tier, link in bio' }
]

describe('mineTemplateGroups', () => {
  const groups = mineTemplateGroups([...SIGNALS, ...RESULTS, ...NOISE])

  it('only forms families from new-signal candidates (results/noise are not families)', () => {
    const total = groups.reduce((sum, group) => sum + group.count, 0)
    expect(total).toBe(SIGNALS.length)
  })

  it('groups structurally identical signals into one family', () => {
    const signalGroup = groups.find((group) => group.count === SIGNALS.length)
    expect(signalGroup).toBeDefined()
    expect(signalGroup.normalizedTemplate).toContain('<INSTRUMENT> <SIDE> MARKET')
  })

  it('suggests accepting a clean high-confidence new-signal family', () => {
    const signalGroup = groups.find((group) => group.count === SIGNALS.length)
    expect(signalGroup.suggestedAction).toBe('accept')
    expect(signalGroup.confidenceAvg).toBeGreaterThan(0.6)
    expect(signalGroup.intentDistribution.new_signal).toBe(SIGNALS.length)
    expect(signalGroup.status).toBe('unreviewed')
  })

  it('does not turn update/result messages into template families', () => {
    expect(groups.some((group) => group.normalizedTemplate.includes('HIT'))).toBe(false)
  })

  it('computes a date range from message dates', () => {
    const signalGroup = groups.find((group) => group.count === SIGNALS.length)
    expect(signalGroup.dateRange).toEqual({ from: '2026-06-01', to: '2026-06-03' })
  })

  it('limits examples to at most five per group', () => {
    for (const group of groups) {
      expect(group.examples.length).toBeLessThanOrEqual(5)
      expect(group.examples.length).toBeGreaterThan(0)
    }
  })

  it('sorts groups by count descending', () => {
    const counts = groups.map((group) => group.count)
    expect(counts).toEqual([...counts].sort((a, b) => b - a))
  })
})

describe('mineTemplateGroups — geometry-broken families never auto-accept', () => {
  const broken = [
    { id: 'g1', text: 'XAUUSD BUY\nEntry 2320\nSL 2340\nTP 2300' },
    { id: 'g2', text: 'XAUUSD BUY\nEntry 2321\nSL 2341\nTP 2301' }
  ]

  it('downgrades a stop/target-inverted family to review', () => {
    const [group] = mineTemplateGroups(broken)
    expect(group.geometryWarnings).toBe(broken.length)
    expect(group.suggestedAction).toBe('review')
  })
})
