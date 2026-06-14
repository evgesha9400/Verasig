/* Verasig prototype — pipeline stepper shown across the verification workflow */
const PIPELINE_STEPS = [
  { id: "backfill", label: "Backfill" },
  { id: "label", label: "Label" },
  { id: "distill", label: "Distill" },
  { id: "verify", label: "Verify" },
  { id: "exchange", label: "Exchange" },
  { id: "risk", label: "Execution" },
  { id: "backtest", label: "Backtest" },
];

// Process steps are loaders (a run, not a configuration) — revisiting them would
// re-execute the run, so they are never directly clickable from the stepper.
const PIPELINE_PROCESS_STEPS = ["backfill", "distill", "backtest"];

function Pipeline({ current, onStepBack }) {
  const idx = PIPELINE_STEPS.findIndex((s) => s.id === current);
  return (
    <div className="vrs-pipe">
      {PIPELINE_STEPS.map((s, i) => {
        const done = i < idx;
        const linkable =
          done && !!onStepBack && !PIPELINE_PROCESS_STEPS.includes(s.id);
        const cls = `vrs-pipe__step ${done ? "is-done" : ""} ${i === idx ? "is-active" : ""}`;
        const inner = (
          <>
            <span className="vrs-pipe__dot">
              {done ? <Icon name="check" size={12} /> : i + 1}
            </span>
            <span className="vrs-pipe__lbl">{s.label}</span>
          </>
        );
        return (
          <React.Fragment key={s.id}>
            {i > 0 && (
              <span className={`vrs-pipe__line ${i <= idx ? "is-done" : ""}`} />
            )}
            {linkable ? (
              <button
                type="button"
                className={`${cls} is-link`}
                title={`Back to ${s.label}`}
                onClick={() => onStepBack(s.id)}
              >
                {inner}
              </button>
            ) : (
              <div className={cls}>{inner}</div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
window.Pipeline = Pipeline;
window.PIPELINE_STEPS = PIPELINE_STEPS;
