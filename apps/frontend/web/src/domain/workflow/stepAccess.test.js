import { describe, expect, it } from 'vitest'
import {
  isStepLocked,
  landingStepForFeed,
  maxStepIndex,
  nextBlockedStep,
  PLAN_MAX_STEP
} from './stepAccess.js'

describe('stepAccess — plan caps', () => {
  it('caps each plan at its furthest step', () => {
    expect(PLAN_MAX_STEP).toEqual({
      observer: 'verify',
      operator: 'backtest',
      desk: 'execution'
    })
  })

  it('orders the caps observer < operator < desk', () => {
    expect(maxStepIndex('observer')).toBeLessThan(maxStepIndex('operator'))
    expect(maxStepIndex('operator')).toBeLessThan(maxStepIndex('desk'))
  })

  it('falls back to operator for an unknown plan', () => {
    expect(maxStepIndex('mystery')).toBe(maxStepIndex('operator'))
  })
})

describe('stepAccess — landing step', () => {
  const feed = (status) => ({ id: 'f', status })

  it('opens a verified feed at Verify for every tier', () => {
    for (const plan of ['observer', 'operator', 'desk']) {
      expect(landingStepForFeed(feed('verified'), plan)).toBe('verify')
    }
  })

  it('opens a backfilled feed at Mine', () => {
    expect(landingStepForFeed(feed('backfilled'), 'observer')).toBe('mine')
    expect(landingStepForFeed(feed('backfilled'), 'desk')).toBe('mine')
  })

  it('opens an analyzed feed at Backtest only when the plan reaches it', () => {
    expect(landingStepForFeed(feed('analyzed'), 'operator')).toBe('backtest')
    expect(landingStepForFeed(feed('analyzed'), 'desk')).toBe('backtest')
    // Observer downgrade edge: caps back to Verify.
    expect(landingStepForFeed(feed('analyzed'), 'observer')).toBe('verify')
  })

  it('opens fresh / in-flight feeds at Backfill', () => {
    for (const status of ['new', 'failed', 'cancelled', 'backfilling']) {
      expect(landingStepForFeed(feed(status), 'operator')).toBe('backfill')
    }
  })

  it('defaults a missing status to Backfill', () => {
    expect(landingStepForFeed({ id: 'f' }, 'operator')).toBe('backfill')
  })
})

describe('stepAccess — locking', () => {
  it('locks steps beyond the plan for an observer', () => {
    expect(isStepLocked('verify', 'observer')).toBe(false)
    expect(isStepLocked('exchange', 'observer')).toBe(true)
    expect(isStepLocked('backtest', 'observer')).toBe(true)
    expect(isStepLocked('execution', 'observer')).toBe(true)
  })

  it('locks only execution for an operator', () => {
    expect(isStepLocked('backtest', 'operator')).toBe(false)
    expect(isStepLocked('execution', 'operator')).toBe(true)
  })

  it('locks nothing for desk', () => {
    for (const step of ['mine', 'verify', 'exchange', 'backtest', 'execution']) {
      expect(isStepLocked(step, 'desk')).toBe(false)
    }
  })
})

describe('stepAccess — next blocked step', () => {
  it('is the first step past the plan cap', () => {
    expect(nextBlockedStep('observer')).toBe('exchange')
    expect(nextBlockedStep('operator')).toBe('execution')
  })

  it('is null when the plan reaches the end of the chain', () => {
    expect(nextBlockedStep('desk')).toBe(null)
  })
})
