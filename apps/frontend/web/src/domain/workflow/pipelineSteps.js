// The feed workflow, flat and ordered. Tiers read left→right: Observer owns
// mine→verify, Operator adds exchange→backtest, Desk adds execution.
// Position ≠ tier: Execution sits after Backtest because it is a Desk
// refinement whose edits re-run the backtest. A future `live` step appends here.
export const PIPELINE_STEPS = [
  { id: 'backfill', label: 'Backfill' },
  { id: 'mine', label: 'Mine' },
  { id: 'review', label: 'Review' },
  { id: 'verify', label: 'Verify' },
  { id: 'exchange', label: 'Exchange' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'execution', label: 'Execution' }
]

// Process steps are loaders (a run, not a configuration) — revisiting them
// re-executes the run, so they are never directly clickable from the stepper.
// Review and Verify are decision steps: revisitable and decision-preserving,
// their rules/audit recompute reactively rather than rerunning a job.
export const PIPELINE_PROCESS_STEPS = ['backfill', 'mine', 'backtest']
