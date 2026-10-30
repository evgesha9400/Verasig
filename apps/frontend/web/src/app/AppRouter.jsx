import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate
} from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Banner, Button, Loader } from '@verasig/design-system'
import { LoginView } from '../features/auth/LoginView.jsx'
import { RegisterView } from '../features/auth/RegisterView.jsx'
import { getCurrentUser, login, logout, register } from '../shared/api/authApi.js'
import { createCheckout } from '../shared/api/billingApi.js'
import { redirectTo } from '../shared/navigation.js'
import { PLANS } from '../domain/plan/planCatalog.js'
import { forgetAuthToken, readAuthToken, rememberAuthToken } from './session.js'
import Marketing from '../features/marketing/MarketingView.jsx'
import { ProductApp } from './ProductApp.jsx'
import { ROUTES } from './paths.js'

function createInitialSession() {
  const token = readAuthToken()

  if (!token) {
    return { status: 'anonymous', token: null, user: null }
  }

  return { status: 'checking', token, user: null }
}

// Only an explicit auth rejection proves the stored token is bad. A network
// failure or server error keeps it so the session survives the outage.
function isRejectedToken(error) {
  return error?.status === 401 || error?.status === 403
}

// `/signup?plan=<id>` names a plan to buy right after registering; only a plan
// that is for sale counts.
function planToBuy(search) {
  const planId = new URLSearchParams(search).get('plan')
  return PLANS.find(
    (plan) => plan.id === planId && plan.available && plan.monthlyPrice > 0
  )
}

function SessionBoot() {
  return (
    <div className="auth-wrap">
      <main className="auth-main">
        <Loader
          variant="bar"
          size="lg"
          title="Welcome back"
          note="Checking your session…"
        />
      </main>
    </div>
  )
}

function SessionUnavailable({ onRetry }) {
  return (
    <div className="auth-wrap">
      <main className="auth-main">
        <Banner
          tone="rejected"
          title="Can't reach Verasig"
          actions={
            <Button variant="primary" size="sm" onClick={onRetry}>
              Try again
            </Button>
          }
        >
          Your session is kept. Try again in a moment.
        </Banner>
      </main>
    </div>
  )
}

export function AppRoutes() {
  const [session, setSession] = useState(createInitialSession)
  const navigate = useNavigate()
  const location = useLocation()
  const authenticated = session.status === 'authenticated'
  const checkingSession = session.status === 'checking'
  const sessionUnavailable = session.status === 'unavailable'

  useEffect(() => {
    if (session.status !== 'checking' || !session.token) return undefined

    let active = true

    getCurrentUser(session.token)
      .then((user) => {
        if (!active) return
        setSession({ status: 'authenticated', token: session.token, user })
      })
      .catch((error) => {
        if (!active) return
        if (!isRejectedToken(error)) {
          setSession({ status: 'unavailable', token: session.token, user: null })
          return
        }
        forgetAuthToken()
        setSession({ status: 'anonymous', token: null, user: null })
      })

    return () => {
      active = false
    }
  }, [session.status, session.token])

  async function authenticateAndOpenProduct(credentials) {
    const authSession = await login(credentials)
    rememberAuthToken(authSession.token)
    setSession({
      status: 'authenticated',
      token: authSession.token,
      user: authSession.user
    })
    navigate(ROUTES.app, { replace: true })
  }

  async function registerAndOpenProduct(account) {
    const authSession = await register(account)
    rememberAuthToken(authSession.token)
    const plan = planToBuy(location.search)
    if (plan) {
      // Both outcomes leave the page; the app boots from the stored token.
      try {
        const { url } = await createCheckout(authSession.token, plan.id, 'month')
        redirectTo(url)
      } catch {
        redirectTo(`${ROUTES.app}?checkout=error`)
      }
      return
    }
    setSession({
      status: 'authenticated',
      token: authSession.token,
      user: authSession.user
    })
    navigate(ROUTES.app, { replace: true })
  }

  function clearSessionAndOpenMarketing() {
    const token = session.token
    forgetAuthToken()
    navigate(ROUTES.marketing, { replace: true })
    setTimeout(() => {
      setSession({ status: 'anonymous', token: null, user: null })
    }, 0)
    if (token) {
      void logout(token).catch(() => {})
    }
  }

  function openLogin() {
    navigate(ROUTES.login)
  }

  function openSignup() {
    navigate(ROUTES.signup)
  }

  return (
    <Routes>
      <Route
        path={ROUTES.marketing}
        element={<Marketing loginPath={ROUTES.login} signupPath={ROUTES.signup} />}
      />
      <Route
        path={ROUTES.login}
        element={
          checkingSession ? (
            <SessionBoot />
          ) : authenticated ? (
            <Navigate to={ROUTES.app} replace />
          ) : (
            <LoginView onLogin={authenticateAndOpenProduct} onRegister={openSignup} />
          )
        }
      />
      <Route
        path={ROUTES.signup}
        element={
          checkingSession ? (
            <SessionBoot />
          ) : authenticated ? (
            <Navigate to={ROUTES.app} replace />
          ) : (
            <RegisterView onRegister={registerAndOpenProduct} onLogin={openLogin} />
          )
        }
      />
      <Route
        path={`${ROUTES.app}/*`}
        element={
          checkingSession ? (
            <SessionBoot />
          ) : sessionUnavailable ? (
            <SessionUnavailable
              onRetry={() => setSession({ ...session, status: 'checking' })}
            />
          ) : authenticated ? (
            <ProductApp
              authToken={session.token}
              user={session.user}
              onLogout={clearSessionAndOpenMarketing}
            />
          ) : (
            <Navigate to={ROUTES.login} replace />
          )
        }
      />
      <Route path="*" element={<Navigate to={ROUTES.marketing} replace />} />
    </Routes>
  )
}

export default function AppRouter() {
  return (
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <AppRoutes />
    </BrowserRouter>
  )
}
