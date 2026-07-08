// FE mirror of the backend signal cap (features/accounts/plans.py PLAN_LIMITS).
//
// The backend stays the enforcement source of truth; this constant drives only
// the client-side Verify preview cap + the "you're capped" notice text. Keep the
// two in sync when a plan's cap changes.
const SIGNAL_LIMIT_BY_PLAN = {
  observer: 200,
  operator: null,
  desk: null
}

// The plan's cap on signals shown, or null when the plan is unlimited.
export function signalLimitFor(plan) {
  return SIGNAL_LIMIT_BY_PLAN[plan] ?? null
}
