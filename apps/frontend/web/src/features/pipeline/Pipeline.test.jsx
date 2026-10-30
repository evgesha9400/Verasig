import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PIPELINE_STEPS } from '../../domain/workflow/pipelineSteps.js'
import { Pipeline } from './Pipeline.jsx'

describe('Pipeline stepper', () => {
  it('renders all step labels', () => {
    render(<Pipeline current="mine" plan="desk" />)
    PIPELINE_STEPS.forEach(({ label }) => {
      expect(screen.getByText(label)).toBeTruthy()
    })
  })

  it('marks steps before current as done', () => {
    const { container } = render(<Pipeline current="verify" plan="desk" />)
    const steps = container.querySelectorAll('.vrs-pipe__step')
    expect(steps[0].classList.contains('is-done')).toBe(true) // backfill
    expect(steps[1].classList.contains('is-done')).toBe(true) // mine
    expect(steps[2].classList.contains('is-done')).toBe(true) // review
    expect(steps[3].classList.contains('is-active')).toBe(true) // verify
  })

  it('locks steps beyond the plan for an observer', () => {
    const { container } = render(<Pipeline current="verify" plan="observer" />)
    const steps = container.querySelectorAll('.vrs-pipe__step')
    expect(steps[3].classList.contains('is-locked')).toBe(false) // verify (reachable)
    expect(steps[4].classList.contains('is-locked')).toBe(true) // exchange
    expect(steps[5].classList.contains('is-locked')).toBe(true) // backtest
    expect(steps[6].classList.contains('is-locked')).toBe(true) // execution
  })

  it('exports PIPELINE_STEPS as the ordered 7-step chain', () => {
    expect(PIPELINE_STEPS.map((s) => s.id)).toEqual([
      'backfill',
      'mine',
      'review',
      'verify',
      'exchange',
      'backtest',
      'execution'
    ])
  })
})
