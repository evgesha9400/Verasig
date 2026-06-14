import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { LoginView } from '../features/auth/LoginView.jsx'
import { RegisterView } from '../features/auth/RegisterView.jsx'
import { getCurrentUser, login, logout, register } from '../shared/api/authApi.js'
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

function SessionBoot() {
  return (
    <div className="auth-wrap">
      <main className="auth-main">
        <div className="auth-form-wrap" role="status">
          Checking session...
        </div>
      </main>
    </div>
  )
}

export function AppRoutes() {
  const [session, setSession] = useState(createInitialSession)
  const navigate = useNavigate()
  const authenticated = session.status === 'authenticated'
  const checkingSession = session.status === 'checking'

  useEffect(() => {
    if (session.status !== 'checking' || !session.token) return undefined

    let active = true

    getCurrentUser(session.token)
      .then((user) => {
        if (!active) return
        setSession({ status: 'authenticated', token: session.token, user })
      })
      .catch(() => {
        if (!active) return
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
