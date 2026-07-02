import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PIPELINE_STEPS } from '../../domain/workflow/pipelineSteps.js'
import { Pipeline } from './Pipeline.jsx'

describe('Pipeline stepper', () => {
  it('renders all step labels', () => {
    render(<Pipeline current="mining" />)
    PIPELINE_STEPS.forEach(({ label }) => {
      expect(screen.getByText(label)).toBeTruthy()
    })
  })

  it('marks steps before current as done', () => {
    const { container } = render(<Pipeline current="exchange" />)
    const steps = container.querySelectorAll('.vrs-pipe__step')
    expect(steps[0].classList.contains('is-done')).toBe(true) // backfill
    expect(steps[1].classList.contains('is-done')).toBe(true) // mining
    expect(steps[2].classList.contains('is-active')).toBe(true) // exchange
  })

  it('exports PIPELINE_STEPS with 5 entries', () => {
    expect(PIPELINE_STEPS).toHaveLength(5)
    expect(PIPELINE_STEPS.map((s) => s.id)).toEqual([
      'backfill',
      'mining',
      'exchange',
      'risk',
      'backtest'
    ])
  })
})
