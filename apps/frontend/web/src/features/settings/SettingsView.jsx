import { useState } from 'react'
import { Card, Input, Button, Badge, Banner } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import {
  cancelEmailChange as cancelEmailChangeRequest,
  changeEmail,
  requestPasswordReset,
  updateProfile
} from '../../shared/api/userApi.js'
import { createCheckout, openBillingPortal } from '../../shared/api/billingApi.js'
import { normalizeAccountName, validateAccountName } from '../../shared/accountName.js'
import { redirectTo } from '../../shared/navigation.js'
import { PLANS } from '../../domain/plan/planCatalog.js'

function errorMessage(error) {
  return error?.message || 'Account update failed. Try again.'
}

// Header badge per Stripe subscription status. No status means never subscribed.
const STATUS_BADGE = {
  trialing: { tone: 'info', label: 'Trial' },
  active: { tone: 'verified', label: 'Active' },
  past_due: { tone: 'rejected', label: 'Past due' },
  unpaid: { tone: 'rejected', label: 'Unpaid' },
  incomplete: { tone: 'pending', label: 'Incomplete' },
  paused: { tone: 'pending', label: 'Paused' },
  canceled: { tone: 'neutral', label: 'Ended' }
}

const PAYMENT_FAILED_STATUSES = new Set(['past_due', 'unpaid'])

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC'
  })
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
          'Email change pending',
          `${updated.pendingEmail} is waiting for confirmation. Email delivery is not available yet.`
        )
      }
    )
  }
  function cancelEmailChange() {
    void applyBackendUser(
      'email',
      () => cancelEmailChangeRequest(authToken),
      (updated) => {
        setEmail(updated.email)
        onToast('info', 'Email change cancelled', `${updated.email} stays active.`)
      }
    )
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
          'Reset requested',
          'Your password reset request was recorded. Email delivery is not available yet.'
        )
      })
      .catch((caughtError) => {
        setResetState('idle')
        showError(caughtError)
      })
  }

  /* ---- subscription ---- */
  // `user.plan` is the effective plan from the backend: free unless Stripe says
  // the subscription is trialing or active.
  const current = PLANS.find((p) => p.id === user.plan) || PLANS[0]
  const freePlan = PLANS[0]
  const hasBilling = Boolean(user.subscriptionStatus)
  const paymentFailed = PAYMENT_FAILED_STATUSES.has(user.subscriptionStatus)
  const statusBadge = user.cancelAt
    ? { tone: 'pending', label: 'Cancelling' }
    : STATUS_BADGE[user.subscriptionStatus]
  const [billingBusy, setBillingBusy] = useState(null) // null | 'month' | 'year' | 'portal'

  async function goToStripe(action, requestUrl) {
    setBillingBusy(action)
    try {
      const { url } = await requestUrl()
      redirectTo(url)
    } catch (caughtError) {
      setBillingBusy(null)
      onToast('rejected', 'Billing unavailable', errorMessage(caughtError))
    }
  }
  function startCheckout(plan, interval) {
    void goToStripe(interval, () => createCheckout(authToken, plan.id, interval))
  }
  function manageBilling() {
    void goToStripe('portal', () => openBillingPortal(authToken))
  }

  function planMeta() {
    if (user.cancelAt) return `Ends ${formatDate(user.cancelAt)} · no further charges`
    if (user.subscriptionStatus === 'trialing') return 'Free trial · billed by Stripe'
    if (current.monthlyPrice > 0) return 'Billed by Stripe'
    return 'Free forever'
  }

  function planAction(plan) {
    if (!plan.available) return <Badge tone="neutral">Coming soon</Badge>
    if (plan.monthlyPrice === 0 || current.monthlyPrice > 0) return null
    return (
      <div className="vrs-plan__actions">
        <Button
          variant="primary"
          size="sm"
          loading={billingBusy === 'month'}
          disabled={billingBusy !== null}
          onClick={() => startCheckout(plan, 'month')}
        >
          {plan.trial ? 'Start 7-day trial' : `Upgrade to ${plan.name}`}
        </Button>
        {plan.yearlyMonthlyPrice != null && (
          <Button
            variant="ghost"
            size="sm"
            loading={billingBusy === 'year'}
            disabled={billingBusy !== null}
            onClick={() => startCheckout(plan, 'year')}
          >
            Pay yearly · ${plan.yearlyMonthlyPrice}/mo
          </Button>
        )}
      </div>
    )
  }

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
              A new address takes effect only after it is confirmed.
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
                <Button
                  variant="ghost"
                  size="sm"
                  loading={busy === 'email'}
                  onClick={cancelEmailChange}
                >
                  Cancel change
                </Button>
              }
            >
              <span className="vrs-mono">{user.pendingEmail}</span> is waiting for
              confirmation. Your current address{' '}
              <span className="vrs-mono">{user.email}</span> stays active until then.
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
              Reset requests are recorded. Email delivery is not available yet.
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
                ? 'Reset requested'
                : resetState === 'sending'
                  ? 'Requesting…'
                  : 'Request reset'}
            </Button>
          </>
        }
      >
        {resetState === 'sent' ? (
          <Banner tone="verified" title="Reset requested">
            The request for <span className="vrs-mono">{user.email}</span> was recorded.
            No reset link was sent because email delivery is not available yet.
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
          statusBadge ? (
            <Badge tone={statusBadge.tone} dot>
              {statusBadge.label}
            </Badge>
          ) : undefined
        }
        footer={
          hasBilling ? (
            <>
              <span className="vrs-help">
                Cancel, resume, change your card and download invoices on Stripe.
              </span>
              <Button
                variant="secondary"
                size="sm"
                loading={billingBusy === 'portal'}
                disabled={billingBusy !== null}
                onClick={manageBilling}
              >
                Manage billing
              </Button>
            </>
          ) : undefined
        }
      >
        <div className="vrs-form">
          <div>
            <div className="vrs-set-plan__name">{current.name}</div>
            <div className="vrs-set-plan__meta vrs-mono">{planMeta()}</div>
          </div>

          {user.cancelAt && (
            <Banner
              tone="pending"
              title={`Subscription ends ${formatDate(user.cancelAt)}`}
            >
              You keep {current.name} until then. After that your account moves to{' '}
              {freePlan.name}: sources stay saved, routing stops. You can resume in
              billing before then.
            </Banner>
          )}

          {paymentFailed && (
            <Banner tone="rejected" title="Payment failed">
              Paid limits are paused until the payment goes through. Update your card in
              billing.
            </Banner>
          )}

          <div className="vrs-plan-grid">
            {PLANS.map((p) => {
              const isCurrent = p.id === current.id
              return (
                <div key={p.id} className={`vrs-plan ${isCurrent ? 'is-current' : ''}`}>
                  <div className="vrs-plan__head">
                    <h3 className="vrs-plan__name">{p.name}</h3>
                    {isCurrent && <Badge tone="verified">Current</Badge>}
                  </div>
                  <div className="vrs-plan__price vrs-mono">
                    ${p.monthlyPrice}
                    <span>/mo</span>
                  </div>
                  <div className="vrs-plan__blurb">{p.tagline}</div>
                  <div className="vrs-plan__feats">
                    {p.includes.map((f) => (
                      <span key={f} className="vrs-plan__feat">
                        <Icon name="check" size={13} /> {f}
                      </span>
                    ))}
                  </div>
                  {!isCurrent && planAction(p)}
                </div>
              )
            })}
          </div>
        </div>
      </Card>
    </div>
  )
}
