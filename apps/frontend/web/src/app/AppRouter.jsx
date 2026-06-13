import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { LoginView } from '../features/auth/LoginView.jsx'
import { RegisterView } from '../features/auth/RegisterView.jsx'
import {
  forgetAuthenticatedUser,
  isAuthenticated,
  rememberAuthenticatedUser
} from './session.js'
import Marketing from '../features/marketing/MarketingView.jsx'
import { ProductApp } from './ProductApp.jsx'
import { ROUTES } from './paths.js'

export function AppRoutes() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated)
  const navigate = useNavigate()

  function authenticateAndOpenProduct() {
    rememberAuthenticatedUser()
    setAuthenticated(true)
    navigate(ROUTES.app, { replace: true })
  }

  function clearSessionAndOpenMarketing() {
    forgetAuthenticatedUser()
    navigate(ROUTES.marketing, { replace: true })
    setTimeout(() => setAuthenticated(false), 0)
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
          authenticated ? (
            <Navigate to={ROUTES.app} replace />
          ) : (
            <LoginView onLogin={authenticateAndOpenProduct} onRegister={openSignup} />
          )
        }
      />
      <Route
        path={ROUTES.signup}
        element={
          authenticated ? (
            <Navigate to={ROUTES.app} replace />
          ) : (
            <RegisterView onRegister={authenticateAndOpenProduct} onLogin={openLogin} />
          )
        }
      />
      <Route
        path={`${ROUTES.app}/*`}
        element={
          authenticated ? (
            <ProductApp onLogout={clearSessionAndOpenMarketing} />
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
