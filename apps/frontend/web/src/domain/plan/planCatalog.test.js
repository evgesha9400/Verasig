import { describe, expect, it } from 'vitest'

import { PLANS } from './planCatalog.js'

const byId = Object.fromEntries(PLANS.map((plan) => [plan.id, plan]))

describe('PLANS', () => {
  it('lists free, trader, desk in order with unique ids', () => {
    expect(PLANS.map((plan) => plan.id)).toEqual(['free', 'trader', 'desk'])
    expect(new Set(PLANS.map((plan) => plan.id)).size).toBe(PLANS.length)
  })

  it('prices plans as the launch spec fixes them', () => {
    expect(byId.free.monthlyPrice).toBe(0)
    expect(byId.trader.monthlyPrice).toBe(49)
    expect(byId.trader.yearlyMonthlyPrice).toBe(39)
    expect(byId.desk.monthlyPrice).toBe(149)
    expect(byId.free.yearlyMonthlyPrice).toBeNull()
    expect(byId.desk.yearlyMonthlyPrice).toBeNull()
  })

  it('offers a trial and the highlight on Trader only', () => {
    expect(PLANS.filter((plan) => plan.trial).map((plan) => plan.id)).toEqual([
      'trader'
    ])
    expect(PLANS.filter((plan) => plan.highlight).map((plan) => plan.id)).toEqual([
      'trader'
    ])
  })

  it('keeps Desk unavailable with no checkout path', () => {
    expect(byId.desk.available).toBe(false)
    expect(byId.desk.ctaPath).toBeNull()
  })

  it('sends the buyable plans to signup', () => {
    expect(byId.free.ctaPath).toBe('/signup')
    expect(byId.trader.ctaPath).toBe('/signup?plan=trader')
  })
})
