import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { LoginView } from './LoginView.jsx'

describe('LoginView', () => {
  it('renders login heading', () => {
    render(<LoginView onLogin={() => {}} onRegister={() => {}} />)
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('calls onLogin when form is submitted', () => {
    const onLogin = vi.fn()
    render(<LoginView onLogin={onLogin} onRegister={() => {}} />)
    fireEvent.submit(screen.getByText('Log in').closest('form'))
    expect(onLogin).toHaveBeenCalledOnce()
  })

  it('calls onRegister when Create an account link clicked', () => {
    const onRegister = vi.fn()
    render(<LoginView onLogin={() => {}} onRegister={onRegister} />)
    fireEvent.click(screen.getByText('Create an account'))
    expect(onRegister).toHaveBeenCalledOnce()
  })
})
