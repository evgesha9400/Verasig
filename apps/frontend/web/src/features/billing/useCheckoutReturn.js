import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getCurrentUser } from '../../shared/api/authApi.js'
import { PLANS } from '../../domain/plan/planCatalog.js'

// Stripe Checkout returns to /app?checkout=success|cancelled. The plan changes
// only when the webhook lands, which is asynchronous, so a success polls the
// account for about ten seconds. Signup sends ?checkout=error when Checkout
// could not start.
const POLL_INTERVAL_MS = 1500
const POLL_ATTEMPTS = 7

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useCheckoutReturn(authToken, { onUser, onToast }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const outcome = searchParams.get('checkout')
  // The query is stripped right away; polling runs on until it ends or unmount.
  const mountedRef = useRef(false)
  const handlingRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!outcome) {
      handlingRef.current = false
      return
    }
    if (handlingRef.current) return
    handlingRef.current = true
    setSearchParams(
      (params) => {
        params.delete('checkout')
        params.delete('session_id')
        return params
      },
      { replace: true }
    )
    if (outcome === 'error') {
      onToast(
        'rejected',
        'Checkout unavailable',
        'Your account is ready. Start the Trader trial from Account settings.'
      )
    }
    if (outcome === 'success') void pollForPlan()

    async function pollForPlan() {
      for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
        if (attempt > 0) await wait(POLL_INTERVAL_MS)
        if (!mountedRef.current) return
        const user = await getCurrentUser(authToken).catch(() => null)
        if (!mountedRef.current) return
        if (user && user.plan !== 'free') {
          const name = PLANS.find((plan) => plan.id === user.plan)?.name || user.plan
          onUser(user)
          onToast('verified', `${name} activated`, `Your ${name} plan is ready to use.`)
          return
        }
      }
      onToast(
        'pending',
        'Payment received',
        'Your plan is still being confirmed. Refresh this page in a minute.'
      )
    }
    // Runs once per Checkout return; the callbacks are not part of the trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outcome, authToken])
}
