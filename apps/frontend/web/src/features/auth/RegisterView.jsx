import { useState } from 'react'
import { Banner, Button, Input, TextLink } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { splitFullName } from '../../shared/accountName.js'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

function errorMessage(error) {
  return error?.message || 'Account creation failed. Check your details and try again.'
}

export function RegisterView({ onRegister, onLogin }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function submitRegistration() {
    const parsed = splitFullName(name)
    if (parsed.error) {
      setError(parsed.error)
      return
    }
    setError(null)
    setSubmitting(true)

    try {
      await onRegister({
        firstName: parsed.firstName,
        lastName: parsed.lastName,
        email: email.trim(),
        password
      })
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  const { error: fullNameError } = splitFullName(name)
  function handleSubmit(event) {
    event.preventDefault()
    void submitRegistration()
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
          <div className="auth-eyebrow">Get started</div>
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-lede">
            Connect a source and verify your first channel in a couple of minutes.
          </p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <Input
              label="Full name"
              name="name"
              autoComplete="name"
              required
              error={fullNameError}
              value={name}
              onChange={(e) => setName(e.target.value)}
              iconLeft={<Icon name="users" size={16} />}
              placeholder="e.g. Mara Voss"
            />
            <Input
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              iconLeft={<Icon name="users" size={16} />}
              placeholder="you@company.com"
            />
            <Input
              label="Password"
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              iconLeft={<Icon name="lock" size={16} />}
              placeholder="••••••••"
              hint="At least 8 characters."
            />
            {error && (
              <Banner tone="rejected" title="Account creation failed">
                {error}
              </Banner>
            )}
            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              loading={submitting}
              disabled={!!fullNameError}
              iconRight={<Icon name="arrowRight" size={16} />}
            >
              Create account
            </Button>
          </form>
          <p className="auth-legal">
            By creating an account you agree to our <a href="#">Terms</a> and{' '}
            <a href="#">Privacy Policy</a>.
          </p>
          <div className="auth-switch">
            Already have an account?{' '}
            <TextLink tone="accent" onClick={onLogin}>
              Log in
            </TextLink>
          </div>
        </div>
      </main>
    </div>
  )
}
