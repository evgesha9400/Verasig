import { useState } from 'react'
import { Banner, Button, Input, TextLink } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

function errorMessage(error) {
  return error?.message || 'Password reset failed. Try again.'
}

export function ResetPasswordView({ token, onSubmit, onDone, onRequestLink }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [invalidLink, setInvalidLink] = useState(!token)
  const [submitting, setSubmitting] = useState(false)

  async function submitPassword() {
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setError(null)
    setSubmitting(true)

    try {
      await onSubmit(token, password)
    } catch (caughtError) {
      setSubmitting(false)
      if (caughtError?.status === 400) setInvalidLink(true)
      else setError(errorMessage(caughtError))
      return
    }
    onDone()
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitPassword()
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
          <div className="auth-eyebrow">Reset password</div>
          <h1 className="auth-title">Set a new password</h1>
          {invalidLink ? (
            <Banner tone="rejected" title="This link is invalid or has expired">
              Reset links work once and expire after 60 minutes.
            </Banner>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit}>
              <Input
                label="New password"
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
              <Input
                label="Confirm new password"
                name="confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                iconLeft={<Icon name="lock" size={16} />}
                placeholder="••••••••"
              />
              {error && (
                <Banner tone="rejected" title="Password not changed">
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
                Set new password
              </Button>
            </form>
          )}
          <div className="auth-switch">
            Need a fresh link?{' '}
            <TextLink tone="accent" onClick={onRequestLink}>
              Request a new link
            </TextLink>
          </div>
        </div>
      </main>
    </div>
  )
}
