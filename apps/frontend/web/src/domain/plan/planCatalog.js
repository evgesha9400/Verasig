// The plan catalogue: names, prices, and what each plan includes.
//
// Single source for every surface that shows plans (landing page, Settings).
// Prices are USD per month. `yearlyMonthlyPrice` is the per-month price when
// billed yearly, or null when the plan has no yearly option. `ctaPath` is null
// for a plan that cannot be bought yet.
export const PLANS = [
  {
    id: 'free',
    name: 'Free check',
    monthlyPrice: 0,
    yearlyMonthlyPrice: null,
    tagline: 'See whether a channel holds up.',
    includes: ['1 feed', 'Reader and scam check', 'Backtest on the latest 200 signals'],
    trial: null,
    available: true,
    highlight: false,
    ctaPath: '/signup'
  },
  {
    id: 'trader',
    name: 'Trader',
    monthlyPrice: 49,
    yearlyMonthlyPrice: 39,
    tagline: 'Trade the feeds you trust.',
    includes: ['10 feeds', 'Full backtests', 'Live trading to 1 Bybit destination'],
    trial: '7-day trial, card required',
    available: true,
    highlight: true,
    ctaPath: '/signup?plan=trader'
  },
  {
    id: 'desk',
    name: 'Desk',
    monthlyPrice: 149,
    yearlyMonthlyPrice: null,
    tagline: 'Many feeds across many accounts.',
    includes: ['Unlimited feeds', 'Many subaccount destinations', 'Webhook later'],
    trial: null,
    available: false,
    highlight: false,
    ctaPath: null
  }
]
