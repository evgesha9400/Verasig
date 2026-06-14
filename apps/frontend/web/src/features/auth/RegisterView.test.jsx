import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RegisterView } from './RegisterView.jsx'

describe('RegisterView', () => {
  it('renders register heading', () => {
    render(<RegisterView onRegister={() => {}} onLogin={() => {}} />)
    expect(screen.getByText('Create your account')).toBeTruthy()
    expect(screen.getByText('At least 8 characters.')).toBeTruthy()
  })

  it('renders empty fields with browser account creation hints', () => {
    render(<RegisterView onRegister={() => {}} onLogin={() => {}} />)

    expect(screen.getByLabelText(/full name/i).value).toBe('')
    expect(screen.getByLabelText(/full name/i).getAttribute('autocomplete')).toBe(
      'name'
    )
    expect(screen.getByLabelText(/email/i).value).toBe('')
    expect(screen.getByLabelText(/email/i).getAttribute('autocomplete')).toBe('email')
    expect(screen.getByLabelText(/password/i).value).toBe('')
    expect(screen.getByLabelText(/password/i).getAttribute('autocomplete')).toBe(
      'new-password'
    )
    expect(screen.getByLabelText(/password/i).getAttribute('minlength')).toBe('8')
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

  it('maps multi-word full names into first and last names', async () => {
    const onRegister = vi.fn().mockResolvedValue()

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: 'Ana María de la Cruz' }
    })
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'ana@example.com' }
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'correct horse battery staple' }
    })
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    await waitFor(() => {
      expect(onRegister).toHaveBeenCalledWith({
        firstName: 'Ana',
        lastName: 'María de la Cruz',
        email: 'ana@example.com',
        password: 'correct horse battery staple'
      })
    })
  })

  it('blocks empty full name submit and shows inline error', async () => {
    const onRegister = vi.fn().mockResolvedValue()

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    expect(await screen.findAllByText('Full name is required.')).toBeTruthy()
    expect(onRegister).not.toHaveBeenCalled()
  })

  it('blocks one-word full name submit and shows inline error', async () => {
    const onRegister = vi.fn().mockResolvedValue()

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: 'Ada' }
    })
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    expect(await screen.findAllByText('Use first and last name.')).toBeTruthy()
    expect(onRegister).not.toHaveBeenCalled()
  })

  it('shows inline error for invalid characters in full name', async () => {
    const onRegister = vi.fn().mockResolvedValue()

    render(<RegisterView onRegister={onRegister} onLogin={() => {}} />)
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: 'Ada 123' }
    })
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    const [message] = await screen.findAllByText(
      'Last name must contain at least one letter.'
    )
    expect(message).toBeTruthy()
    expect(onRegister).not.toHaveBeenCalled()
  })

  it('shows backend registration errors without navigating', async () => {
    const onRegister = vi
      .fn()
      .mockRejectedValue(new Error('Email is already registered'))

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

    expect(await screen.findAllByText('Email is already registered')).toBeTruthy()
  })

  it('calls onLogin when Log in link is clicked', () => {
    const onLogin = vi.fn()

    render(<RegisterView onRegister={() => {}} onLogin={onLogin} />)
    fireEvent.click(screen.getByText('Log in'))

    expect(onLogin).toHaveBeenCalledOnce()
  })
})
