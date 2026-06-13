import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from './AppRouter.jsx'

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
    }
  }
}

function installTestStorage() {
  const storage = createTestStorage()
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true
  })
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    configurable: true
  })
}

function renderRoute(initialPath) {
  return render(
    <MemoryRouter
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      initialEntries={[initialPath]}
    >
      <AppRoutes />
    </MemoryRouter>
  )
}

beforeEach(() => {
  installTestStorage()
})

describe('AppRoutes', () => {
  it('renders the marketing landing at root', () => {
    renderRoute('/')
    const h1 = screen.getByRole('heading', { level: 1 })
    expect(h1.textContent).toContain('Verify the signal')
    expect(h1.textContent).toContain('before you trade it.')
  })

  it('routes marketing Sign up links to signup', () => {
    renderRoute('/')
    const signups = screen.getAllByRole('link', { name: /sign up/i })
    expect(signups.length).toBeGreaterThan(0)
    for (const link of signups) {
      expect(link.getAttribute('href')).toBe('/signup')
    }
  })

  it('routes marketing Log in links to login', () => {
    renderRoute('/')
    const logins = screen.getAllByRole('link', { name: /log in/i })
    expect(logins.length).toBeGreaterThan(0)
    for (const link of logins) {
      expect(link.getAttribute('href')).toBe('/login')
    }
  })

  it('updates marketing theme through shared DS radio semantics', async () => {
    const user = userEvent.setup()
    renderRoute('/')

    await user.click(screen.getByRole('radio', { name: 'Light' }))

    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.documentElement.style.getPropertyValue('--accent')).toBe('#8FB81E')
  })

  it('navigates from login submit to the product shell', async () => {
    renderRoute('/login')
    fireEvent.submit(screen.getByText('Log in').closest('form'))
    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
  })

  it('navigates from register submit to the product shell', async () => {
    renderRoute('/signup')
    fireEvent.submit(screen.getByText('Create account').closest('form'))
    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
  })

  it('redirects unauthenticated app visits to login', async () => {
    renderRoute('/app')
    await waitFor(() => {
      expect(screen.getByText('Log in to Verasig')).toBeTruthy()
    })
  })

  it('supports signup to product to logout to landing', async () => {
    const user = userEvent.setup()
    renderRoute('/')

    await user.click(screen.getAllByRole('link', { name: /sign up/i })[0])
    fireEvent.submit(screen.getByText('Create account').closest('form'))

    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })

    await user.click(screen.getByRole('button', { expanded: false }))
    await user.click(screen.getByRole('menuitem', { name: /log out/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 }).textContent).toContain(
        'Verify the signal'
      )
    })
  })
})
