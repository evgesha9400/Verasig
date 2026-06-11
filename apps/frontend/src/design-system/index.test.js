import { describe, it, expect } from 'vitest'
import * as DS from './index.js'

describe('design-system barrel', () => {
  const expected = [
    'Avatar', 'Badge', 'Button', 'IconButton', 'Tabs', 'Tag',
    'Card', 'ConfidenceBar', 'MetricStat', 'SignalRow', 'StatusPill',
    'Banner', 'Dialog', 'Toast', 'ToastStack', 'Tooltip',
    'Checkbox', 'Input', 'Select', 'Switch',
    'Icon',
  ]
  it.each(expected)('exports %s', (name) => {
    expect(typeof DS[name]).toBe('function')
  })
})
