import { useState } from 'react'
import { Banner, Button, Input, Checkbox } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

function errorMessage(error) {
  return error?.message || 'Login failed. Check your details and try again.'
}

export function LoginView({ onLogin, onRegister }) {
  const [email, setEmail] = useState('mara@northwave.io')
  const [password, setPassword] = useState('verasig-demo-2026')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function submitLogin() {
    setError(null)
    setSubmitting(true)

    try {
      await onLogin({
        email: email.trim(),
        password
      })
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitLogin()
  }

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="#">
            <Icon name="sources" size={24} />
            Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
          </a>
          <div className="auth-eyebrow">Welcome back</div>
          <h1 className="auth-title">Log in to Verasig</h1>
          <p className="auth-lede">Pick up where your sources left off.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <Input
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              iconLeft={<Icon name="users" size={16} />}
              placeholder="you@company.com"
            />
            <Input
              label="Password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              iconLeft={<Icon name="lock" size={16} />}
              placeholder="••••••••"
            />
            <div className="auth-row">
              <Checkbox label="Remember me" defaultChecked />
              <a className="auth-forgot" href="#">
                Forgot password?
              </a>
            </div>
            {error && (
              <Banner tone="rejected" title="Login failed">
                {error}
              </Banner>
            )}
            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              loading={submitting}
              iconRight={<Icon name="arrowRight" size={16} />}
            >
              Log in
            </Button>
          </form>
          <div className="auth-switch">
            New to Verasig?{' '}
            <button type="button" className="auth-link" onClick={onRegister}>
              Create an account
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
