import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@verasig/design-system'
import AppRouter, { AppRoutes } from './AppRouter.jsx'

const AUTH_TOKEN_KEY = 'vrs-auth-token-1'
const THEME_STORAGE_KEY = 'vrs-theme-1'
const backendUser = {
  firstName: 'Ada',
  lastName: 'Lovelace',
  email: 'ada@example.com',
  plan: 'observer',
  pendingEmail: null,
  cancelAt: null
}
const backendFeed = {
  id: '7',
  name: 'Pilot Signals',
  tag: '@pilot',
  subscribers: 1234,
  initials: 'PS',
  tint: 'var(--viz-1)',
  status: 'new',
  fetched: 0,
  lastDate: null,
  score: null,
  winRate: null,
  pnl: null,
  hasRisk: false,
  historyGaps: false,
  signalDeletion: false,
  deletedCount: 0
}

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

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

function emptyResponse(status = 204) {
  return new Response(null, { status })
}

function installFetch(routes = {}) {
  globalThis.fetch = vi.fn((url, options = {}) => {
    const method = options.method || 'GET'
    const path = new URL(url).pathname
    const route = routes[`${method} ${path}`]

    if (!route) {
      return Promise.reject(new Error(`Unexpected request: ${method} ${path}`))
    }

    return Promise.resolve(route(url, options))
  })
}

class FakeEventSource {
  constructor(url) {
    this.url = url
    this.closed = false
    this.listeners = {}
    FakeEventSource.last = this
  }

  addEventListener(type, listener) {
    this.listeners[type] = listener
  }

  close() {
    this.closed = true
  }

  emit(type, data) {
    this.listeners[type]({
      data: data === undefined ? undefined : JSON.stringify(data)
    })
  }
}

function sourceRoutes({
  telegram = { connected: false, phone: null },
  feeds = []
} = {}) {
  return {
    'GET /telegram/status': () => jsonResponse(telegram),
    'GET /feeds': () => jsonResponse({ feeds })
  }
}

function renderRoute(initialPath) {
  // AppRoutes consumes useTheme, so it must mount under a ThemeProvider exactly
  // as it does in production (AppRouter wraps it). Rendering it bare would now
  // throw — the competing-fallback footgun useTheme used to hide.
  return render(
    <ThemeProvider>
      <MemoryRouter
        future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
        initialEntries={[initialPath]}
      >
        <AppRoutes />
      </MemoryRouter>
    </ThemeProvider>
  )
}

beforeEach(() => {
  installTestStorage()
  installFetch()
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.removeAttribute('style')
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
    expect(document.documentElement.style.getPropertyValue('--accent')).toBe('#5197FF')
  })

  it('applies the stored theme on auth pages that never call useTheme', async () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')
    window.history.pushState({}, '', '/login')

    render(<AppRouter />)

    await waitFor(() => {
      expect(screen.getByText('Log in to Verasig')).toBeTruthy()
    })
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.documentElement.style.getPropertyValue('--accent')).toBe('#5197FF')
  })

  it('navigates from backend login submit to the product shell', async () => {
    installFetch({
      'POST /auth/login': () =>
        jsonResponse({ token: 'login-token', user: backendUser }),
      ...sourceRoutes()
    })

    renderRoute('/login')
    fireEvent.submit(screen.getByText('Log in').closest('form'))

    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('login-token')
    expect(screen.getByText('ada@example.com')).toBeTruthy()
  })

  it('navigates from backend register submit to the product shell', async () => {
    installFetch({
      'POST /auth/register': () =>
        jsonResponse({ token: 'register-token', user: backendUser }, 201),
      ...sourceRoutes()
    })

    renderRoute('/signup')
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
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('register-token')
    expect(screen.getByText('ada@example.com')).toBeTruthy()
  })

  it('redirects unauthenticated app visits to login', async () => {
    renderRoute('/app')
    await waitFor(() => {
      expect(screen.getByText('Log in to Verasig')).toBeTruthy()
    })
  })

  it('loads the product shell from a stored token and current backend user', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'stored-token')
    installFetch({
      'GET /auth/me': () => jsonResponse(backendUser),
      ...sourceRoutes()
    })

    renderRoute('/app')

    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
    expect(screen.getByText('Ada Lovelace')).toBeTruthy()
    expect(screen.getByText('ada@example.com')).toBeTruthy()
  })

  it('hydrates Telegram status and feeds from the backend after session reload', async () => {
    const user = userEvent.setup()
    localStorage.setItem(AUTH_TOKEN_KEY, 'stored-token')
    installFetch({
      'GET /auth/me': () => jsonResponse(backendUser),
      ...sourceRoutes({
        telegram: { connected: true, phone: '+44 •••• 8821' },
        feeds: [backendFeed]
      })
    })

    renderRoute('/app')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /telegram/i })).toBeTruthy()
    })
    await user.click(screen.getByRole('button', { name: /telegram/i }))

    expect(await screen.findByText('Pilot Signals')).toBeTruthy()
  })

  it('starts streamed deletion rescan from Check gaps and shows signal toast', async () => {
    const user = userEvent.setup()
    let feedReads = 0
    globalThis.EventSource = FakeEventSource
    localStorage.setItem(AUTH_TOKEN_KEY, 'stored-token')
    installFetch({
      'GET /auth/me': () => jsonResponse(backendUser),
      'GET /telegram/status': () =>
        jsonResponse({ connected: true, phone: '+44 •••• 8821' }),
      'GET /feeds': () => {
        feedReads += 1
        const feed =
          feedReads === 1
            ? { ...backendFeed, status: 'verified' }
            : {
                ...backendFeed,
                status: 'verified',
                signalDeletion: true,
                deletedCount: 1
              }
        return jsonResponse({ feeds: [feed] })
      },
      'POST /feeds/7/deletion-rescan': () =>
        jsonResponse({ jobId: 'user:7:deletion-rescan' }, 202)
    })

    renderRoute('/app')

    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
    await user.click(screen.getByRole('button', { name: /telegram/i }))
    expect(await screen.findByText('Pilot Signals')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Options' }))
    await user.click(screen.getByRole('menuitem', { name: /check gaps/i }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/feeds/7/deletion-rescan',
        {
          method: 'POST',
          headers: { Authorization: 'Bearer stored-token' }
        }
      )
    })
    expect(FakeEventSource.last.url).toBe(
      'http://localhost:8000/feeds/7/deletion-rescan/progress?token=stored-token'
    )

    await act(async () => {
      FakeEventSource.last.emit('done', {
        newDeletedSignalCount: 1,
        newDeletedNonSignalCount: 0,
        newSuspectedGapCount: 0,
        totalDeletedCount: 1,
        signalDeletion: true
      })
    })

    expect(await screen.findByText('Signal deletion confirmed')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText('Scam')).toBeTruthy()
    })
    expect(screen.getByText('1 deleted')).toBeTruthy()
  })

  it('shows verified feed signals from the backend Signals tab', async () => {
    const user = userEvent.setup()
    localStorage.setItem(AUTH_TOKEN_KEY, 'stored-token')
    installFetch({
      'GET /auth/me': () => jsonResponse(backendUser),
      ...sourceRoutes({
        telegram: { connected: true, phone: '+44 •••• 8821' },
        feeds: [{ ...backendFeed, status: 'verified' }]
      }),
      'GET /signals': () =>
        jsonResponse({
          signals: [
            {
              id: 'sig-1',
              feedId: '7',
              feedName: 'Pilot Signals',
              feedTag: '@pilot',
              feedInitials: 'PS',
              feedTint: 'var(--viz-1)',
              source: 'telegram',
              side: 'LONG',
              symbol: 'BTCUSDT',
              status: 'untested',
              date: 'Jun 6',
              time: '12:00',
              entry: '100',
              stop: '95',
              tp: ['110'],
              text: 'BTC long entry',
              deleted: false,
              cancelled: false,
              mods: [],
              effective: { entry: '100', stop: '95', tp: ['110'] }
            }
          ],
          orphanMods: [],
          limitReached: false
        })
    })

    renderRoute('/app')

    await waitFor(() => {
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })
    await user.click(screen.getByRole('button', { name: /signals/i }))

    expect(await screen.findByText('BTC/USDT')).toBeTruthy()
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/signals', {
      method: 'GET',
      headers: { Authorization: 'Bearer stored-token' }
    })
  })

  it('clears an invalid stored token before redirecting to login', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'bad-token')
    installFetch({
      'GET /auth/me': () =>
        jsonResponse(
          {
            error: {
              code: 'AUTH_INVALID_TOKEN',
              message: 'Invalid token'
            }
          },
          401
        )
    })

    renderRoute('/app')

    await waitFor(() => {
      expect(screen.getByText('Log in to Verasig')).toBeTruthy()
    })
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('supports signup to product to backend logout to landing', async () => {
    const user = userEvent.setup()
    installFetch({
      'POST /auth/register': () =>
        jsonResponse({ token: 'register-token', user: backendUser }, 201),
      'POST /auth/logout': () => emptyResponse(),
      ...sourceRoutes()
    })
    renderRoute('/')

    await user.click(screen.getAllByRole('link', { name: /sign up/i })[0])
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
      expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
    })

    await user.click(screen.getByRole('button', { expanded: false }))
    await user.click(screen.getByRole('menuitem', { name: /log out/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 }).textContent).toContain(
        'Verify the signal'
      )
    })
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/auth/logout', {
      method: 'POST',
      headers: { Authorization: 'Bearer register-token' }
    })
  })
})
