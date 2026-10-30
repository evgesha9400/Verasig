// Plan-aware step access for the feed workflow.
//
// A feed opens at the last step it can act on, capped by what the user's plan
// unlocks — and the user can never navigate past the next locked step. This
// module is the single source of truth for both rules; the UI (routing +
// stepper) only calls these helpers.

import { PIPELINE_STEPS } from './pipelineSteps.js'

// The furthest step each plan can reach (inclusive). Forward-compatible: adding
// a `live` step + a `desk`/new tier is a one-line change here.
export const PLAN_MAX_STEP = {
  free: 'verify',
  trader: 'backtest',
  desk: 'execution'
}

// An unknown plan unlocks no more than the free plan.
const DEFAULT_PLAN = 'free'

// Where a feed opens by status, before capping by plan. Completed loaders hand
// off to the next actionable step (backfilled → mine, analyzed → backtest).
const LANDING_STEP_BY_STATUS = {
  new: 'backfill',
  failed: 'backfill',
  cancelled: 'backfill',
  backfilling: 'backfill',
  backfilled: 'mine',
  verified: 'verify',
  analyzed: 'backtest'
}

function stepIndex(stepId) {
  return PIPELINE_STEPS.findIndex((step) => step.id === stepId)
}

function planCapStep(plan) {
  return PLAN_MAX_STEP[plan] || PLAN_MAX_STEP[DEFAULT_PLAN]
}

// Highest step index the plan unlocks.
export function maxStepIndex(plan) {
  return stepIndex(planCapStep(plan))
}

// The step a feed should open at: its last actionable step, never beyond the
// plan cap. A verified feed opens at Verify for every tier (Backtest is a later
// step that has not run yet); a free user never lands past Verify.
export function landingStepForFeed(feed, plan) {
  const status = feed?.status || 'new'
  const mappedIndex = stepIndex(LANDING_STEP_BY_STATUS[status] || 'backfill')
  const cappedIndex = Math.min(mappedIndex, maxStepIndex(plan))
  return PIPELINE_STEPS[cappedIndex].id
}

// A step is locked when it sits beyond what the plan unlocks.
export function isStepLocked(stepId, plan) {
  return stepIndex(stepId) > maxStepIndex(plan)
}

// The cheapest plan that reaches a step (plans are listed cheapest first).
export function unlockingPlan(stepId) {
  return Object.keys(PLAN_MAX_STEP).find((plan) => !isStepLocked(stepId, plan))
}
