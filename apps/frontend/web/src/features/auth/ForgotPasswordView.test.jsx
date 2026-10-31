import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../shared/api/client.js'
import { ForgotPasswordView } from './ForgotPasswordView.jsx'

const CONFIRMATION = /If an account exists for that address, a reset link is on its way/

function submitEmail(value) {
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value } })
  fireEvent.submit(screen.getByLabelText(/email/i).closest('form'))
}

describe('ForgotPasswordView', () => {
  it('renders one email field', () => {
    render(<ForgotPasswordView onSubmit={() => {}} onLogin={() => {}} />)

    expect(screen.getByText('Reset your password')).toBeTruthy()
    expect(screen.getByLabelText(/email/i).getAttribute('autocomplete')).toBe('email')
  })

  it('submits the trimmed email and confirms', async () => {
    const onSubmit = vi.fn().mockResolvedValue()
    render(<ForgotPasswordView onSubmit={onSubmit} onLogin={() => {}} />)

    submitEmail('  ada@example.com ')

    expect(await screen.findByText(CONFIRMATION)).toBeTruthy()
    expect(onSubmit).toHaveBeenCalledWith('ada@example.com')
  })

  it('shows an outage when the server answers 5xx', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new ApiError({ status: 502, code: 'HTTP_502', message: 'x' }))
    render(<ForgotPasswordView onSubmit={onSubmit} onLogin={() => {}} />)

    submitEmail('ada@example.com')

    expect(await screen.findByText("Can't reach Verasig")).toBeTruthy()
    expect(screen.queryByText(CONFIRMATION)).toBeNull()
  })

  it('shows a network failure and lets the user retry', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    render(<ForgotPasswordView onSubmit={onSubmit} onLogin={() => {}} />)

    submitEmail('ada@example.com')

    expect(await screen.findByText("Can't reach Verasig")).toBeTruthy()
    expect(screen.queryByText(CONFIRMATION)).toBeNull()
  })

  it('shows a rejected address next to the form', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'HTTP_422',
        message: 'Email: value is not a valid email address'
      })
    )
    render(<ForgotPasswordView onSubmit={onSubmit} onLogin={() => {}} />)

    submitEmail('ada@example')

    expect(
      await screen.findByText('Email: value is not a valid email address')
    ).toBeTruthy()
    expect(screen.queryByText(CONFIRMATION)).toBeNull()
  })

  it('links back to log in', async () => {
    const onLogin = vi.fn()
    render(<ForgotPasswordView onSubmit={() => {}} onLogin={onLogin} />)

    fireEvent.click(screen.getByText('Back to log in'))

    await waitFor(() => expect(onLogin).toHaveBeenCalledOnce())
  })
})
