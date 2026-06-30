import { describe, expect, it } from 'vitest'
import { formatConfidence } from './format.js'

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
