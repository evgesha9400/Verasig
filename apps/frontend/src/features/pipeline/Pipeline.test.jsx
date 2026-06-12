import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Pipeline, PIPELINE_STEPS } from './Pipeline.jsx'

describe('Pipeline stepper', () => {
  it('renders all step labels', () => {
    render(<Pipeline current="label" />)
    PIPELINE_STEPS.forEach(({ label }) => {
      expect(screen.getByText(label)).toBeTruthy()
    })
  })

  it('marks steps before current as done', () => {
    const { container } = render(<Pipeline current="distill" />)
    const steps = container.querySelectorAll('.vrs-pipe__step')
    expect(steps[0].classList.contains('is-done')).toBe(true) // backfill
    expect(steps[1].classList.contains('is-done')).toBe(true) // label
    expect(steps[2].classList.contains('is-active')).toBe(true) // distill
  })

  it('exports PIPELINE_STEPS with 7 entries', () => {
    expect(PIPELINE_STEPS).toHaveLength(7)
    expect(PIPELINE_STEPS.map((s) => s.id)).toEqual([
      'backfill',
      'label',
      'distill',
      'verify',
      'exchange',
      'risk',
      'backtest'
    ])
  })
})
