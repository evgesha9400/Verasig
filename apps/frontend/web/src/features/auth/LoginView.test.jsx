import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { LoginView } from './LoginView.jsx'

describe('LoginView', () => {
  it('renders login heading', () => {
    render(<LoginView onLogin={() => {}} onRegister={() => {}} />)
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('renders empty fields with browser login hints', () => {
    render(<LoginView onLogin={() => {}} onRegister={() => {}} />)

    expect(screen.getByLabelText(/email/i).value).toBe('')
    expect(screen.getByLabelText(/email/i).getAttribute('autocomplete')).toBe('email')
    expect(screen.getByLabelText(/password/i).value).toBe('')
    expect(screen.getByLabelText(/password/i).getAttribute('autocomplete')).toBe(
      'current-password'
    )
    expect(screen.getByRole('checkbox', { name: /remember me/i }).checked).toBe(false)
  })

  it('calls onLogin with the typed credentials when form is submitted', async () => {
    const onLogin = vi.fn().mockResolvedValue()
    render(<LoginView onLogin={onLogin} onRegister={() => {}} />)

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'ada@example.com' }
    })
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'correct horse battery staple' }
    })
    fireEvent.submit(screen.getByText('Log in').closest('form'))

    await waitFor(() => {
      expect(onLogin).toHaveBeenCalledWith({
        email: 'ada@example.com',
        password: 'correct horse battery staple'
      })
    })
  })

  it('shows backend login errors without navigating', async () => {
    const onLogin = vi.fn().mockRejectedValue(new Error('Invalid email or password'))

    render(<LoginView onLogin={onLogin} onRegister={() => {}} />)
    fireEvent.submit(screen.getByText('Log in').closest('form'))

    expect(await screen.findByText('Invalid email or password')).toBeTruthy()
  })

  it('calls onRegister when Create an account link clicked', () => {
    const onRegister = vi.fn()
    render(<LoginView onLogin={() => {}} onRegister={onRegister} />)
    fireEvent.click(screen.getByText('Create an account'))
    expect(onRegister).toHaveBeenCalledOnce()
  })
})
