import { describe, expect, it } from 'vitest'
import { byMessageDateDesc, formatConfidence, formatMessageDate } from './format.js'

describe('formatConfidence', () => {
  it('formats a ratio as a rounded percent', () => {
    expect(formatConfidence(0.875)).toBe('88%')
    expect(formatConfidence(0.5)).toBe('50%')
  })

  it('returns a dash for a missing or non-numeric value, never NaN%', () => {
    expect(formatConfidence(undefined)).toBe('—')
    expect(formatConfidence(null)).toBe('—')
    expect(formatConfidence(Number.NaN)).toBe('—')
  })
})

describe('formatMessageDate', () => {
  it('returns an empty string for a missing date', () => {
    expect(formatMessageDate('')).toBe('')
    expect(formatMessageDate(undefined)).toBe('')
    expect(formatMessageDate(null)).toBe('')
  })

  it('passes a human/demo date through unchanged', () => {
    expect(formatMessageDate('Jun 6 08:42')).toBe('Jun 6 08:42')
  })

  it('reformats an ISO timestamp into a compact label (no raw T)', () => {
    const out = formatMessageDate('2026-06-01T08:42:00Z')
    expect(out).not.toContain('T')
    expect(out).toContain('2026')
  })

  it('never throws and returns an unparseable value as-is', () => {
    expect(() => formatMessageDate('not a date')).not.toThrow()
    expect(formatMessageDate('not a date')).toBe('not a date')
  })
})

describe('byMessageDateDesc', () => {
  const dateOf = (item) => item.date
  const sortByDate = (items) => [...items].sort(byMessageDateDesc(dateOf))

  it('orders parseable dates newest-first', () => {
    const out = sortByDate([
      { id: 'a', date: '2026-06-01T00:00:00Z' },
      { id: 'b', date: '2026-06-09T00:00:00Z' },
      { id: 'c', date: '2026-06-05T00:00:00Z' }
    ]).map((item) => item.id)
    expect(out).toEqual(['b', 'c', 'a'])
  })

  it('sorts a dated item ahead of an undated one', () => {
    const out = sortByDate([
      { id: 'undated' },
      { id: 'dated', date: '2026-06-01T00:00:00Z' }
    ]).map((item) => item.id)
    expect(out).toEqual(['dated', 'undated'])
  })

  it('holds input order for two undated items (stable)', () => {
    const out = sortByDate([{ id: 'x' }, { id: 'y' }]).map((item) => item.id)
    expect(out).toEqual(['x', 'y'])
  })
})
