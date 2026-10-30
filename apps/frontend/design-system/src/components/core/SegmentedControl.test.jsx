import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SegmentedControl } from './SegmentedControl.jsx'

const options = [
  { value: 'd', label: 'Day' },
  { value: 'w', label: 'Week' },
  { value: 'm', label: 'Month' }
]

describe('SegmentedControl keyboard navigation', () => {
  it('moves real DOM focus onto the newly-selected segment', () => {
    const { getByRole } = render(
      <SegmentedControl value="d" onChange={vi.fn()} options={options} label="Range" />
    )
    const group = getByRole('radiogroup')
    fireEvent.keyDown(group, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(getByRole('radio', { name: 'Week' }))
  })

  it('moves focus to the last segment on End', () => {
    const { getByRole } = render(
      <SegmentedControl value="d" onChange={vi.fn()} options={options} label="Range" />
    )
    fireEvent.keyDown(getByRole('radiogroup'), { key: 'End' })
    expect(document.activeElement).toBe(getByRole('radio', { name: 'Month' }))
  })
})
