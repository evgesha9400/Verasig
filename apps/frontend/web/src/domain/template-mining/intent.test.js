import { describe, expect, it } from 'vitest'
import { classifyIntent } from './intent.js'
import { extractSignalFields } from './fields.js'

function intentOf(text) {
  return classifyIntent(text, extractSignalFields(text))
}

describe('classifyIntent — new signals', () => {
  it('classifies a full market signal as new_signal', () => {
    expect(intentOf('XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355')).toBe('new_signal')
  })

  it('classifies a range sell signal as new_signal', () => {
    expect(intentOf('Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800')).toBe(
      'new_signal'
    )
  })

  it('classifies a no-entry signal with risk levels as new_signal', () => {
    expect(intentOf('BTC LONG\nSL 67400\nTP 69000\nTP 70500')).toBe('new_signal')
  })
})

describe('classifyIntent — results', () => {
  it('treats a TP hit as a result', () => {
    expect(intentOf('XAUUSD BUY hit TP1 ✅')).toBe('result')
  })

  it('treats an SL hit as a result', () => {
    expect(intentOf('ETH short hit SL')).toBe('result')
  })

  it('treats a closed trade with points as a result', () => {
    expect(intentOf('US30 buy closed +150 points')).toBe('result')
  })

  it('treats running pips as a result', () => {
    expect(intentOf('BTC long running +300 pips')).toBe('result')
  })
})

describe('classifyIntent — updates', () => {
  it('treats moving stop to break-even as an update', () => {
    expect(intentOf('Move SL to BE on gold buy')).toBe('update')
  })

  it('treats a close command as an update', () => {
    expect(intentOf('Close BTC long now')).toBe('update')
  })

  it('treats a cancel as an update', () => {
    expect(intentOf('Cancel EURUSD sell')).toBe('update')
  })
})

describe('classifyIntent — commentary', () => {
  it('treats a directional opinion without structure as commentary', () => {
    expect(intentOf('Gold looks bullish today but wait for confirmation')).toBe(
      'commentary'
    )
  })

  it('treats analysis without a direction as commentary', () => {
    expect(intentOf('XAUUSD analysis: price may reject from 2330')).toBe('commentary')
  })
})
