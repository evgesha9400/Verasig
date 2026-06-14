import { useState } from 'react'
import { Card, Input, Button, Badge, Banner, Dialog } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import {
  cancelSubscription,
  changeEmail,
  changeSubscription,
  requestPasswordReset,
  resumeSubscription as resumeSubscriptionRequest,
  updateProfile
} from '../../shared/api/userApi.js'
import { normalizeAccountName, validateAccountName } from '../../shared/accountName.js'

function errorMessage(error) {
  return error?.message || 'Account update failed. Try again.'
}

export function SettingsView({ authToken, user, onUpdateUser, onToast }) {
  const [busy, setBusy] = useState(null)

  function showError(error) {
    onToast('rejected', 'Account update failed', errorMessage(error))
  }

  async function applyBackendUser(action, requestUser, announceSuccess) {
    setBusy(action)

    try {
      const updated = await requestUser()
      onUpdateUser(updated)
      announceSuccess(updated)
    } catch (caughtError) {
      showError(caughtError)
    } finally {
      setBusy(null)
    }
  }

  /* ---- profile ---- */
  const [first, setFirst] = useState(user.firstName)
  const [last, setLast] = useState(user.lastName)
  const normalizedFirst = normalizeAccountName(first)
  const normalizedLast = normalizeAccountName(last)
  const userFirst = normalizeAccountName(user.firstName)
  const userLast = normalizeAccountName(user.lastName)
  const firstNameError = validateAccountName(normalizedFirst, 'First name')
  const lastNameError = validateAccountName(normalizedLast, 'Last name')
  const sameNameError =
    normalizedFirst &&
    normalizedLast &&
    normalizedFirst.toLowerCase() === normalizedLast.toLowerCase()
      ? 'First and last name must be different.'
      : null
  const profileDirty = normalizedFirst !== userFirst || normalizedLast !== userLast
  const profileValid = !firstNameError && !lastNameError && !sameNameError
  function saveProfile() {
    void applyBackendUser(
      'profile',
      () =>
        updateProfile(authToken, {
          firstName: normalizedFirst,
          lastName: normalizedLast
        }),
      (updated) =>
        onToast(
          'verified',
          'Profile updated',
          `Your name is now ${updated.firstName} ${updated.lastName}.`
        )
    )
  }

  /* ---- email ---- */
  const [email, setEmail] = useState(user.pendingEmail || user.email)
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
  const emailDirty =
    email.trim() !== user.email && email.trim() !== (user.pendingEmail || '')
  function saveEmail() {
    void applyBackendUser(
      'email',
      () => changeEmail(authToken, email.trim()),
      (updated) => {
        setEmail(updated.pendingEmail || updated.email)
        onToast(
          'info',
          'Verification sent',
          `Check ${updated.pendingEmail} and click the link to confirm the change.`
        )
      }
    )
  }
  function cancelEmailChange() {
    onUpdateUser({ pendingEmail: null })
    setEmail(user.email)
  }

  /* ---- password ---- */
  const [resetState, setResetState] = useState('idle') // idle | sending | sent
  function sendReset() {
    if (resetState !== 'idle') return
    setResetState('sending')
    requestPasswordReset(authToken)
      .then(() => {
        setResetState('sent')
        onToast(
          'verified',
          'Reset link sent',
          `A password reset link is on its way to ${user.email}.`
        )
      })
      .catch((caughtError) => {
        setResetState('idle')
        showError(caughtError)
      })
  }

  /* ---- subscription ---- */
  const PLANS = [
    {
      id: 'observer',
      name: 'Observer',
      price: 0,
      blurb: 'Watch before you trust.',
      feats: ['1 source', '200 signals / mo', 'Manual review only']
    },
    {
      id: 'operator',
      name: 'Operator',
      price: 49,
      blurb: 'Verify and route, live.',
      feats: ['10 sources', 'Unlimited signals', '1 exchange']
    },
    {
      id: 'desk',
      name: 'Desk',
      price: 190,
      blurb: 'For teams running size.',
      feats: ['Unlimited sources', 'Multi-exchange routing', 'API access']
    }
  ]
  const current = PLANS.find((p) => p.id === user.plan) || PLANS[1]
  const [planTarget, setPlanTarget] = useState(null)
  const [cancelOpen, setCancelOpen] = useState(false)
  function choosePlan(p) {
    if (p.id === user.plan) return
    if (p.price === 0) {
      setCancelOpen(true)
      return
    }
    setPlanTarget(p)
  }
  function confirmPlan() {
    const p = planTarget
    setPlanTarget(null)
    void applyBackendUser(
      'subscription',
      () => changeSubscription(authToken, p.id),
      () =>
        onToast(
          'verified',
          'Plan changed',
          `You're on ${p.name} now. The difference is prorated on your next invoice.`
        )
    )
  }
  function confirmCancel() {
    setCancelOpen(false)
    void applyBackendUser(
      'subscription',
      () => cancelSubscription(authToken),
      () =>
        onToast(
          'pending',
          'Subscription cancelled',
          `${current.name} stays active until the end of the billing period.`
        )
    )
  }
  function resumeSubscription() {
    void applyBackendUser(
      'subscription',
      () => resumeSubscriptionRequest(authToken),
      () =>
        onToast(
          'verified',
          'Subscription resumed',
          `${current.name} will renew as usual.`
        )
    )
  }

  const planUpDown = (p) => (p.price > current.price ? 'Upgrade' : 'Downgrade')

  return (
    <div className="vrs-page vrs-set">
      {/* ---- Profile ---- */}
      <Card
        title="Profile"
        subtitle="How your name appears across Verasig"
        footer={
          <>
            <span className="vrs-help">
              Shown in the workspace menu and on audit-log entries.
            </span>
            <Button
              variant="primary"
              size="sm"
              disabled={!profileDirty || !profileValid}
              onClick={saveProfile}
              loading={busy === 'profile'}
            >
              Save
            </Button>
          </>
        }
      >
        <div className="vrs-form">
          <div className="vrs-form__row">
            <Input
              label="First name"
              value={first}
              onChange={(e) => setFirst(e.target.value)}
              required
              error={firstNameError || sameNameError}
            />
            <Input
              label="Last name"
              value={last}
              onChange={(e) => setLast(e.target.value)}
              required
              error={lastNameError || sameNameError}
            />
          </div>
        </div>
      </Card>

      {/* ---- Email ---- */}
      <Card
        title="Email"
        subtitle="Where alerts, invoices and security notices go"
        footer={
          <>
            <span className="vrs-help">
              We&rsquo;ll send a verification link before the change takes effect.
            </span>
            <Button
              variant="primary"
              size="sm"
              disabled={!emailDirty || !emailValid}
              onClick={saveEmail}
              loading={busy === 'email'}
            >
              Save
            </Button>
          </>
        }
      >
        <div className="vrs-form">
          <Input
            label="Email address"
            mono
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            iconLeft={<Icon name="doc" size={15} />}
            required
            error={
              email.trim().length > 0 && !emailValid
                ? 'Enter a valid email address.'
                : undefined
            }
          />
          {user.pendingEmail && (
            <Banner
              tone="pending"
              title="Verification pending"
              actions={
                <>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      onToast(
                        'info',
                        'Verification re-sent',
                        `A fresh link is on its way to ${user.pendingEmail}.`
                      )
                    }
                  >
                    Resend link
                  </Button>
                  <Button variant="ghost" size="sm" onClick={cancelEmailChange}>
                    Cancel change
                  </Button>
                </>
              }
            >
              We sent a confirmation link to{' '}
              <span className="vrs-mono">{user.pendingEmail}</span>. Your current
              address <span className="vrs-mono">{user.email}</span> stays active until
              it&rsquo;s confirmed.
            </Banner>
          )}
        </div>
      </Card>

      {/* ---- Password ---- */}
      <Card
        title="Password"
        subtitle="Reset by email — we never show or store it in plain text"
        footer={
          <>
            <span className="vrs-help">
              The link expires after 60 minutes. Active sessions stay signed in.
            </span>
            <Button
              variant="secondary"
              size="sm"
              loading={resetState === 'sending'}
              disabled={resetState === 'sent'}
              onClick={sendReset}
              iconLeft={resetState === 'idle' ? <Icon name="lock" size={15} /> : null}
            >
              {resetState === 'sent'
                ? 'Link sent'
                : resetState === 'sending'
                  ? 'Sending…'
                  : 'Send reset link'}
            </Button>
          </>
        }
      >
        {resetState === 'sent' ? (
          <Banner tone="verified" title="Reset link sent">
            Check <span className="vrs-mono">{user.email}</span> and follow the link to
            set a new password.
          </Banner>
        ) : (
          <div className="vrs-set-pass">
            <span className="vrs-set-pass__dots vrs-mono">••••••••••••</span>
            <span className="vrs-help">Last changed Feb 12, 2026</span>
          </div>
        )}
      </Card>

      {/* ---- Subscription ---- */}
      <Card
        title="Subscription"
        subtitle="Plan, billing and renewal"
        headerActions={
          user.cancelAt ? (
            <Badge tone="pending" dot>
              Cancelling
            </Badge>
          ) : (
            <Badge tone="verified" dot>
              Active
            </Badge>
          )
        }
        footer={
          !user.cancelAt && user.plan !== 'observer' ? (
            <>
              <span className="vrs-help">
                Cancelling keeps {current.name} active until the end of the billing
                period.
              </span>
              <Button variant="danger" size="sm" onClick={() => setCancelOpen(true)}>
                Cancel subscription
              </Button>
            </>
          ) : undefined
        }
      >
        <div className="vrs-form">
          <div className="vrs-row-between">
            <div>
              <div className="vrs-set-plan__name">{current.name}</div>
              <div className="vrs-set-plan__meta vrs-mono">
                {user.cancelAt
                  ? `Ends ${user.cancelAt} · no further charges`
                  : current.price === 0
                    ? 'Free forever'
                    : 'Renews Jul 8, 2026 · billed monthly'}
              </div>
            </div>
            <div className="vrs-set-plan__price vrs-mono">
              ${current.price}
              <span>/mo</span>
            </div>
          </div>

          {user.cancelAt && (
            <Banner
              tone="pending"
              title={`Subscription ends ${user.cancelAt}`}
              actions={
                <Button variant="secondary" size="sm" onClick={resumeSubscription}>
                  Resume subscription
                </Button>
              }
            >
              You keep full {current.name} access until then. After that your account
              drops to Observer — sources stay saved, routing stops.
            </Banner>
          )}

          <div className="vrs-plan-grid">
            {PLANS.map((p) => {
              const isCurrent = p.id === user.plan
              return (
                <div key={p.id} className={`vrs-plan ${isCurrent ? 'is-current' : ''}`}>
                  <div className="vrs-plan__head">
                    <span className="vrs-plan__name">{p.name}</span>
                    {isCurrent && <Badge tone="verified">Current</Badge>}
                  </div>
                  <div className="vrs-plan__price vrs-mono">
                    ${p.price}
                    <span>/mo</span>
                  </div>
                  <div className="vrs-plan__blurb">{p.blurb}</div>
                  <div className="vrs-plan__feats">
                    {p.feats.map((f) => (
                      <span key={f} className="vrs-plan__feat">
                        <Icon name="check" size={13} /> {f}
                      </span>
                    ))}
                  </div>
                  {!isCurrent && (
                    <Button
                      variant={p.price > current.price ? 'primary' : 'ghost'}
                      size="sm"
                      onClick={() => choosePlan(p)}
                    >
                      {p.price === 0 ? 'Downgrade' : `${planUpDown(p)} to ${p.name}`}
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </Card>

      {/* ---- dialogs ---- */}
      <Dialog
        open={!!planTarget}
        onClose={() => setPlanTarget(null)}
        title={planTarget ? `${planUpDown(planTarget)} to ${planTarget.name}?` : ''}
        description={planTarget ? `$${planTarget.price}/mo, prorated from today.` : ''}
        icon={<Icon name="arrowUp" size={19} />}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setPlanTarget(null)}>
              Keep {current.name}
            </Button>
            <Button variant="primary" size="sm" onClick={confirmPlan}>
              {planTarget ? `Switch to ${planTarget.name}` : ''}
            </Button>
          </>
        }
      >
        The change applies immediately. Your next invoice on Jul 8, 2026 includes the
        prorated difference. Sources, labels and exchange connections are untouched.
      </Dialog>

      <Dialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        title="Cancel subscription?"
        description={`${current.name} stays active until Jul 8, 2026.`}
        icon={<Icon name="alert" size={19} />}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setCancelOpen(false)}>
              Keep {current.name}
            </Button>
            <Button variant="danger" size="sm" onClick={confirmCancel}>
              Cancel subscription
            </Button>
          </>
        }
      >
        After Jul 8 your account drops to Observer: 1 source, 200 signals a month, no
        exchange routing. Your sources, labels and backtest history are kept. You can
        resume any time before then.
      </Dialog>
    </div>
  )
}
