import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RegisterView } from './RegisterView.jsx'

describe('RegisterView', () => {
  it('renders register heading', () => {
    render(<RegisterView onRegister={() => {}} onLogin={() => {}} />)
    expect(screen.getByText('Create your account')).toBeTruthy()
  })

  it('calls onRegister with backend registration fields', async () => {
    const onRegister = vi.fn().mockResolvedValue()

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: 'Ada Lovelace' }
    })
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'ada@example.com' }
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'correct horse battery staple' }
    })
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    await waitFor(() => {
      expect(onRegister).toHaveBeenCalledWith({
        firstName: 'Ada',
        lastName: 'Lovelace',
        email: 'ada@example.com',
        password: 'correct horse battery staple'
      })
    })
  })

  it('shows backend registration errors without navigating', async () => {
    const onRegister = vi
      .fn()
      .mockRejectedValue(new Error('Email is already registered'))

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    expect(await screen.findByText('Email is already registered')).toBeTruthy()
  })

  it('calls onLogin when Log in link is clicked', () => {
    const onLogin = vi.fn()

    render(<RegisterView onRegister={() => {}} onLogin={onLogin} />)
    fireEvent.click(screen.getByText('Log in'))

    expect(onLogin).toHaveBeenCalledOnce()
  })
})
