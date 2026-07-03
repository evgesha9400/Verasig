/* Verasig — Mining sub-step progress bar (Mine → Review → Verify).
   Shown at the top of the Mining wizard step; only Review is reachable by click
   (going back from Verify). Mine is a process step — never clickable. */

const STEPS = [
  { id: 'mine', label: 'Mine' },
  { id: 'review', label: 'Review' },
  { id: 'verify', label: 'Verify' }
]

export function MiningStepBar({ active, canVerify = false, onNavigate = () => {} }) {
  const activeIndex = STEPS.findIndex((step) => step.id === active)
  return (
    <div className="vrs-tm-steps" role="list">
      {STEPS.map((step, index) => {
        const isActive = index === activeIndex
        const isDone = index < activeIndex
        // Review is always reachable (back from Verify); Verify only once at
        // least one template is accepted; Mine is a process step — never.
        const clickable =
          (step.id === 'review' && active === 'verify') ||
          (step.id === 'verify' && canVerify && active === 'review')
        const cls = [
          'vrs-tm-step',
          isActive ? 'is-active' : '',
          isDone ? 'is-done' : ''
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <button
            key={step.id}
            type="button"
            role="listitem"
            className={cls}
            aria-current={isActive ? 'step' : undefined}
            disabled={!clickable}
            onClick={clickable ? () => onNavigate(step.id) : undefined}
          >
            <span className="vrs-tm-step__n">{index + 1}</span>
            <span className="vrs-tm-step__label">{step.label}</span>
          </button>
        )
      })}
    </div>
  )
}
