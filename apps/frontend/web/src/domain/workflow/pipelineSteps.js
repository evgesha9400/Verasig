export const PIPELINE_STEPS = [
  { id: 'backfill', label: 'Backfill' },
  { id: 'mining', label: 'Mining' },
  { id: 'exchange', label: 'Exchange' },
  { id: 'risk', label: 'Execution' },
  { id: 'backtest', label: 'Backtest' }
]

// Process steps are loaders (a run, not a configuration) — revisiting them would
// re-execute the run, so they are never directly clickable from the stepper.
// Mining is intentionally excluded: it is revisitable and decision-preserving,
// its rules/audit recompute reactively from decisions rather than rerunning a job.
export const PIPELINE_PROCESS_STEPS = ['backfill', 'backtest']
