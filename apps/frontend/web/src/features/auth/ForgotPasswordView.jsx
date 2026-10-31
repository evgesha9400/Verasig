import { useState } from 'react'
import { Banner, Button, Input, TextLink } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

// No HTTP status means the fetch never reached the API; a 5xx means the API or
// the proxy in front of it is down. Either way no reset link was sent.
function isOutage(error) {
  return error?.status === undefined || error.status >= 500
}

export function ForgotPasswordView({ onSubmit, onLogin }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [unreachable, setUnreachable] = useState(false)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function submitEmail() {
    setUnreachable(false)
    setError(null)
    setSubmitting(true)

    try {
      await onSubmit(email.trim())
      setSent(true)
    } catch (caughtError) {
      // The API answers 202 for every valid address, so an error reveals nothing.
      if (isOutage(caughtError)) setUnreachable(true)
      else setError(caughtError.message)
    } finally {
      setSubmitting(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitEmail()
  }

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="/">
            <Icon name="sources" size={24} />
            Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
          </a>
          <div className="auth-eyebrow">Forgot password</div>
          <h1 className="auth-title">Reset your password</h1>
          <p className="auth-lede">
            Enter your account email and we will send you a link to set a new password.
          </p>
          {sent ? (
            <Banner tone="verified" title="Check your inbox">
              If an account exists for that address, a reset link is on its way. It
              expires in 60 minutes.
            </Banner>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit}>
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
              {error && (
                <Banner tone="rejected" title="Check the address">
                  {error}
                </Banner>
              )}
              {unreachable && (
                <Banner tone="rejected" title="Can't reach Verasig">
                  Check your connection and try again.
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
                Email me a reset link
              </Button>
            </form>
          )}
          <div className="auth-switch">
            Remembered it?{' '}
            <TextLink tone="accent" onClick={onLogin}>
              Back to log in
            </TextLink>
          </div>
        </div>
      </main>
    </div>
  )
}
