import { describe, expect, it } from 'vitest'
import {
  isStepLocked,
  landingStepForFeed,
  maxStepIndex,
  PLAN_MAX_STEP,
  unlockingPlan
} from './stepAccess.js'

describe('stepAccess — plan caps', () => {
  it('caps each plan at its furthest step', () => {
    expect(PLAN_MAX_STEP).toEqual({
      free: 'verify',
      trader: 'backtest',
      desk: 'execution'
    })
  })

  it('orders the caps free < trader < desk', () => {
    expect(maxStepIndex('free')).toBeLessThan(maxStepIndex('trader'))
    expect(maxStepIndex('trader')).toBeLessThan(maxStepIndex('desk'))
  })

  it('falls back to free for an unknown plan', () => {
    expect(maxStepIndex('mystery')).toBe(maxStepIndex('free'))
  })
})

describe('stepAccess — landing step', () => {
  const feed = (status) => ({ id: 'f', status })

  it('opens a verified feed at Verify for every tier', () => {
    for (const plan of ['free', 'trader', 'desk']) {
      expect(landingStepForFeed(feed('verified'), plan)).toBe('verify')
    }
  })

  it('opens a backfilled feed at Mine', () => {
    expect(landingStepForFeed(feed('backfilled'), 'free')).toBe('mine')
    expect(landingStepForFeed(feed('backfilled'), 'desk')).toBe('mine')
  })

  it('opens an analyzed feed at Backtest only when the plan reaches it', () => {
    expect(landingStepForFeed(feed('analyzed'), 'trader')).toBe('backtest')
    expect(landingStepForFeed(feed('analyzed'), 'desk')).toBe('backtest')
    // Free downgrade edge: caps back to Verify.
    expect(landingStepForFeed(feed('analyzed'), 'free')).toBe('verify')
  })

  it('opens fresh / in-flight feeds at Backfill', () => {
    for (const status of ['new', 'failed', 'cancelled', 'backfilling']) {
      expect(landingStepForFeed(feed(status), 'trader')).toBe('backfill')
    }
  })

  it('defaults a missing status to Backfill', () => {
    expect(landingStepForFeed({ id: 'f' }, 'trader')).toBe('backfill')
  })
})

describe('stepAccess — locking', () => {
  it('locks steps beyond the plan for a free user', () => {
    expect(isStepLocked('verify', 'free')).toBe(false)
    expect(isStepLocked('exchange', 'free')).toBe(true)
    expect(isStepLocked('backtest', 'free')).toBe(true)
    expect(isStepLocked('execution', 'free')).toBe(true)
  })

  it('locks only execution for a trader', () => {
    expect(isStepLocked('backtest', 'trader')).toBe(false)
    expect(isStepLocked('execution', 'trader')).toBe(true)
  })

  it('locks nothing for desk', () => {
    for (const step of ['mine', 'verify', 'exchange', 'backtest', 'execution']) {
      expect(isStepLocked(step, 'desk')).toBe(false)
    }
  })
})

describe('stepAccess — unlocking plan', () => {
  it('names the cheapest plan that reaches a step', () => {
    expect(unlockingPlan('verify')).toBe('free')
    expect(unlockingPlan('exchange')).toBe('trader')
    expect(unlockingPlan('backtest')).toBe('trader')
    expect(unlockingPlan('execution')).toBe('desk')
  })
})
