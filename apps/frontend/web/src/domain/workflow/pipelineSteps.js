export const PIPELINE_STEPS = [
  { id: 'backfill', label: 'Backfill' },
  { id: 'label', label: 'Label' },
  { id: 'distill', label: 'Distill' },
  { id: 'verify', label: 'Verify' },
  { id: 'exchange', label: 'Exchange' },
  { id: 'risk', label: 'Execution' },
  { id: 'backtest', label: 'Backtest' }
]

// Process steps are loaders (a run, not a configuration) — revisiting them would
// re-execute the run, so they are never directly clickable from the stepper.
export const PIPELINE_PROCESS_STEPS = ['backfill', 'distill', 'backtest']
