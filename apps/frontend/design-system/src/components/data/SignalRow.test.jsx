import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SignalRow } from './SignalRow.jsx'

describe('SignalRow', () => {
  it('exposes an interactive row as a keyboard-operable button', () => {
    const onClick = vi.fn()
    const { getByRole } = render(<SignalRow symbol="BTC" onClick={onClick} />)
    const row = getByRole('button')
    expect(row.getAttribute('tabindex')).toBe('0')
    fireEvent.keyDown(row, { key: 'Enter' })
    fireEvent.keyDown(row, { key: ' ' })
    expect(onClick).toHaveBeenCalledTimes(2)
  })

  it('stays a plain row with no keyboard affordance when not interactive', () => {
    const { container } = render(<SignalRow symbol="BTC" />)
    const row = container.firstChild
    expect(row.getAttribute('role')).toBeNull()
    expect(row.getAttribute('tabindex')).toBeNull()
  })
})
