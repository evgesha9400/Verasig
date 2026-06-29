import { Fragment } from 'react'
import { Icon } from '@verasig/design-system'

/* Verasig — Template Mining: the workflow ribbon.
   Mirrors the verification stepper (reuses .vrs-pipe) so the prototype reads as
   part of the same product: Messages → Candidates → Templates → Review → Rules → Audit. */
const STAGES = [
  { id: 'messages', label: 'Messages' },
  { id: 'candidates', label: 'Candidates' },
  { id: 'templates', label: 'Templates' },
  { id: 'review', label: 'Review' },
  { id: 'rules', label: 'Rules' },
  { id: 'audit', label: 'Audit' }
]

export function MiningPipelineRibbon({ activeId }) {
  const activeIndex = STAGES.findIndex((stage) => stage.id === activeId)
  return (
    <div className="vrs-pipe">
      {STAGES.map((stage, index) => {
        const done = index < activeIndex
        const cls = `vrs-pipe__step ${done ? 'is-done' : ''} ${index === activeIndex ? 'is-active' : ''}`
        return (
          <Fragment key={stage.id}>
            {index > 0 && (
              <span
                className={`vrs-pipe__line ${index <= activeIndex ? 'is-done' : ''}`}
              />
            )}
            <div className={cls}>
              <span className="vrs-pipe__dot">
                {done ? <Icon name="check" size={12} /> : index + 1}
              </span>
              <span className="vrs-pipe__lbl">{stage.label}</span>
            </div>
          </Fragment>
        )
      })}
    </div>
  )
}
