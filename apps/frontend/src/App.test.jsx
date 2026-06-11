import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import App from './App.jsx'

function createTestStorage() {
  const entries = new Map()

  return {
    getItem: (key) => {
      const storageKey = String(key)
      return entries.has(storageKey) ? entries.get(storageKey) : null
    },
    setItem: (key, value) => {
      entries.set(String(key), String(value))
    },
    removeItem: (key) => {
      entries.delete(String(key))
    },
    clear: () => {
      entries.clear()
    },
  }
}

beforeEach(() => {
  const storage = createTestStorage()
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  })
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    configurable: true,
  })
})

describe('App auth flow', () => {
  it('shows login screen by default', () => {
    render(<App />)
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('navigates to register from login', () => {
    render(<App />)
    fireEvent.click(screen.getByText('Create an account'))
    expect(screen.getByText('Create your account')).toBeTruthy()
  })

  it('navigates back to login from register', () => {
    render(<App />)
    fireEvent.click(screen.getByText('Create an account'))
    fireEvent.click(screen.getByText('Log in'))
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('enters main app shell after login', () => {
    render(<App />)
    fireEvent.submit(screen.getByText('Log in').closest('form'))
    expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
  })
})
