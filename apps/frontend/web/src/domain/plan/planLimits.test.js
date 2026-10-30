import { describe, expect, it } from 'vitest'

import { signalLimitFor } from './planLimits.js'

describe('signalLimitFor', () => {
  it('caps the free plan at 200', () => {
    expect(signalLimitFor('free')).toBe(200)
  })

  it('leaves paid plans unlimited', () => {
    expect(signalLimitFor('trader')).toBeNull()
    expect(signalLimitFor('desk')).toBeNull()
  })

  it('treats an unknown plan as unlimited', () => {
    expect(signalLimitFor(undefined)).toBeNull()
    expect(signalLimitFor('mystery')).toBeNull()
  })
})
