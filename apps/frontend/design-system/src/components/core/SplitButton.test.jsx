import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SplitButton } from './SplitButton.jsx'

const OPTIONS = [
  { value: '6m', label: '6 months' },
  { value: '1y', label: '1 year' },
  { value: 'all', label: 'All history' }
]

function renderSplit(props = {}) {
  return render(
    <SplitButton options={OPTIONS} value="1y" {...props}>
      Start backfill
    </SplitButton>
  )
}

describe('SplitButton', () => {
  it('fires the main action and never opens the menu on a main click', () => {
    const onClick = vi.fn()
    const { getByText, queryByRole } = renderSplit({ onClick })
    fireEvent.click(getByText('Start backfill'))
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(queryByRole('menu')).toBeNull()
  })

  it('opens the menu from the toggle and lists every option', () => {
    const { getByLabelText, getByText, getByRole } = renderSplit()
    fireEvent.click(getByLabelText('Choose option'))
    expect(getByRole('menu')).toBeTruthy()
    expect(getByText('6 months')).toBeTruthy()
    expect(getByText('All history')).toBeTruthy()
  })

  it('fires onSelect with the chosen value and closes the menu', () => {
    const onSelect = vi.fn()
    const { getByLabelText, getByText, queryByRole } = renderSplit({ onSelect })
    fireEvent.click(getByLabelText('Choose option'))
    fireEvent.click(getByText('6 months'))
    expect(onSelect).toHaveBeenCalledWith('6m')
    expect(queryByRole('menu')).toBeNull()
  })

  it('marks the active option with a check icon', () => {
    const { getByLabelText, getByText } = renderSplit()
    fireEvent.click(getByLabelText('Choose option'))
    const active = getByText('1 year').closest('[role="menuitem"]')
    const other = getByText('6 months').closest('[role="menuitem"]')
    expect(active.querySelector('svg')).toBeTruthy()
    expect(other.querySelector('svg')).toBeNull()
  })

  it('disables both halves when disabled', () => {
    const { getByText, getByLabelText } = renderSplit({ disabled: true })
    expect(getByText('Start backfill').closest('button').disabled).toBe(true)
    expect(getByLabelText('Choose option').disabled).toBe(true)
  })
})
