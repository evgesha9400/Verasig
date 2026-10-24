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

  it('keeps focus inside and calls the latest onClose when re-rendered with a new closure', () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()
    const first = vi.fn()
    const latest = vi.fn()

    const { getByLabelText, rerender } = render(
      <Dialog open title="Confirm" onClose={() => first()} />
    )
    getByLabelText('Close').focus()
    rerender(<Dialog open title="Confirm" onClose={() => latest()} />)

    expect(document.activeElement).toBe(getByLabelText('Close'))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(first).not.toHaveBeenCalled()
    expect(latest).toHaveBeenCalledTimes(1)
    trigger.remove()
  })

  it('labels the dialog by its title and describes it by its description', () => {
    const { getByRole, getByText } = render(
      <Dialog open title="Confirm" description="Are you sure?" onClose={() => {}} />
    )
    const dialog = getByRole('dialog')
    expect(dialog.getAttribute('aria-labelledby')).toBe(getByText('Confirm').id)
    expect(dialog.getAttribute('aria-describedby')).toBe(getByText('Are you sure?').id)
  })

  it('moves focus to the first focusable element when it opens', () => {
    const { getByLabelText } = render(
      <Dialog open title="Confirm" onClose={() => {}} />
    )
    expect(document.activeElement).toBe(getByLabelText('Close'))
  })

  it('focuses the panel itself when it has nothing focusable', () => {
    const { getByRole } = render(<Dialog open title="Notice" />)
    expect(document.activeElement).toBe(getByRole('dialog'))
  })

  it('wraps Tab and Shift+Tab inside the dialog', () => {
    const { getByLabelText, getByText } = render(
      <Dialog open title="Confirm" onClose={() => {}} footer={<button>OK</button>} />
    )
    const close = getByLabelText('Close')
    const ok = getByText('OK')
    ok.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(close)
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(ok)
  })
})
