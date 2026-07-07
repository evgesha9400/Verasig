import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Dialog } from './Dialog.jsx'

describe('Dialog', () => {
  it('gives the close button type="button" so it never submits a form', () => {
    const { getByLabelText } = render(
      <Dialog open title="Confirm" onClose={() => {}} />
    )
    expect(getByLabelText('Close').getAttribute('type')).toBe('button')
  })

  it('closes on Escape', () => {
    const onClose = vi.fn()
    render(<Dialog open title="Confirm" onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('restores focus to the previously-focused element when it unmounts', () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    const { unmount } = render(<Dialog open title="Confirm" onClose={() => {}} />)
    unmount()
    expect(document.activeElement).toBe(trigger)
    trigger.remove()
  })
})
