import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../shared/api/client.js'
import { ResetPasswordView } from './ResetPasswordView.jsx'

const INVALID = 'This link is invalid or has expired'

function renderReset(props = {}) {
  const handlers = {
    onSubmit: vi.fn().mockResolvedValue(),
    onDone: vi.fn(),
    onRequestLink: vi.fn()
  }
  render(<ResetPasswordView token="reset-token" {...handlers} {...props} />)
  return { ...handlers, ...props }
}

function fillAndSubmit(password, confirm = password) {
  fireEvent.change(screen.getByLabelText('New password'), {
    target: { value: password }
  })
  fireEvent.change(screen.getByLabelText('Confirm new password'), {
    target: { value: confirm }
  })
  fireEvent.submit(screen.getByLabelText('New password').closest('form'))
}

describe('ResetPasswordView', () => {
  it('renders new and confirm password fields', () => {
    renderReset()

    expect(screen.getByText('Set a new password')).toBeTruthy()
    expect(screen.getByLabelText('New password').getAttribute('autocomplete')).toBe(
      'new-password'
    )
  })

  it('submits the token and the new password, then finishes', async () => {
    const { onSubmit, onDone } = renderReset()

    fillAndSubmit('a brand new passphrase')

    await waitFor(() => expect(onDone).toHaveBeenCalledOnce())
    expect(onSubmit).toHaveBeenCalledWith('reset-token', 'a brand new passphrase')
  })

  it('stops on a confirmation mismatch without calling the API', async () => {
    const { onSubmit } = renderReset()

    fillAndSubmit('a brand new passphrase', 'a different passphrase')

    expect(await screen.findByText('Passwords do not match')).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the invalid-link state when the API rejects the token', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({
        status: 400,
        code: 'AUTH_INVALID_TOKEN',
        message: 'Invalid or expired link'
      })
    )
    const { onRequestLink } = renderReset({ onSubmit })

    fillAndSubmit('a brand new passphrase')

    expect(await screen.findByText(INVALID)).toBeTruthy()
    fireEvent.click(screen.getByText('Request a new link'))
    expect(onRequestLink).toHaveBeenCalledOnce()
  })

  it('shows the invalid-link state when the link has no token', () => {
    renderReset({ token: '' })

    expect(screen.getByText(INVALID)).toBeTruthy()
    expect(screen.queryByLabelText('New password')).toBeNull()
  })

  it('shows other API errors next to the form', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'HTTP_422',
        message: 'Password: String should have at most 72 characters'
      })
    )
    renderReset({ onSubmit })

    fillAndSubmit('a brand new passphrase')

    expect(
      await screen.findByText('Password: String should have at most 72 characters')
    ).toBeTruthy()
    expect(screen.getByLabelText('New password')).toBeTruthy()
  })
})
