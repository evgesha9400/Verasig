import { describe, expect, it } from 'vitest'
import { normalizeMessageText } from './text.js'

describe('normalizeMessageText', () => {
  it('keeps the original text untouched for display', () => {
    const result = normalizeMessageText('XAUUSD   BUY')
    expect(result.original).toBe('XAUUSD   BUY')
  })

  it('collapses repeated whitespace inside a line', () => {
    const result = normalizeMessageText('XAUUSD    BUY   NOW')
    expect(result.clean).toBe('XAUUSD BUY NOW')
  })

  it('normalizes non-breaking and unicode spaces to a regular space', () => {
    const result = normalizeMessageText('BUY XAUUSD NOW')
    expect(result.clean).toBe('BUY XAUUSD NOW')
  })

  it('strips thousands separators inside numbers', () => {
    const result = normalizeMessageText('entry 68,500')
    expect(result.clean).toBe('entry 68500')
  })

  it('strips thousands separators across multi-group numbers', () => {
    const result = normalizeMessageText('1,234,567')
    expect(result.clean).toBe('1234567')
  })

  it('preserves a price range and normalizes its dash', () => {
    const result = normalizeMessageText('Entry 2320–2325')
    expect(result.clean).toBe('Entry 2320-2325')
  })

  it('keeps a plain hyphen price range intact', () => {
    const result = normalizeMessageText('2320-2325')
    expect(result.clean).toBe('2320-2325')
  })

  it('exposes a lowercased view for matching', () => {
    const result = normalizeMessageText('GOLD Long Now')
    expect(result.lower).toBe('gold long now')
  })

  it('splits clean text into trimmed non-empty lines preserving structure', () => {
    const result = normalizeMessageText('XAUUSD BUY\n\n  SL 2312  \nTP 2340')
    expect(result.lines).toEqual(['XAUUSD BUY', 'SL 2312', 'TP 2340'])
  })

  it('handles emoji without crashing or dropping the direction word', () => {
    const result = normalizeMessageText('🟢 GOLD LONG 🚀')
    expect(result.clean).toContain('GOLD LONG')
    expect(result.clean).toContain('🟢')
  })

  it('treats empty input as empty output', () => {
    const result = normalizeMessageText('')
    expect(result.clean).toBe('')
    expect(result.lines).toEqual([])
  })
})
