import { Fragment } from 'react'
import { Icon } from '@verasig/design-system'
import {
  PIPELINE_PROCESS_STEPS,
  PIPELINE_STEPS
} from '../../domain/workflow/pipelineSteps.js'
import { maxStepIndex } from '../../domain/workflow/stepAccess.js'

/* Verasig prototype — pipeline stepper shown across the verification workflow.
   Steps beyond the user's plan are locked: rendered with a lock and never
   clickable, so the user sees — but cannot cross — their next upgrade gate. */
export function Pipeline({ current, plan, onStepBack }) {
  const idx = PIPELINE_STEPS.findIndex((s) => s.id === current)
  const maxIdx = maxStepIndex(plan)
  return (
    <div className="vrs-pipe">
      {PIPELINE_STEPS.map((s, i) => {
        const locked = i > maxIdx
        const done = i < idx
        const linkable =
          done && !locked && !!onStepBack && !PIPELINE_PROCESS_STEPS.includes(s.id)
        const cls = `vrs-pipe__step ${done ? 'is-done' : ''} ${
          i === idx ? 'is-active' : ''
        } ${locked ? 'is-locked' : ''}`
        const inner = (
          <>
            <span className="vrs-pipe__dot">
              {locked ? (
                <Icon name="lock" size={11} />
              ) : done ? (
                <Icon name="check" size={12} />
              ) : (
                i + 1
              )}
            </span>
            <span className="vrs-pipe__lbl">{s.label}</span>
          </>
        )
        return (
          <Fragment key={s.id}>
            {i > 0 && (
              <span className={`vrs-pipe__line ${i <= idx ? 'is-done' : ''}`} />
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
          </Fragment>
        )
      })}
    </div>
  )
}
