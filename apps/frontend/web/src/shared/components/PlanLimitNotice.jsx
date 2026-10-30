import { Banner, Button } from '@verasig/design-system'

/* Verasig — shared "you're capped" affordance.
   The single notice shown wherever a plan truncates the signals a user sees
   (Signals list + Verify preview), so both read identically. Presentational:
   the parent decides `shown` and owns the upgrade navigation via `onUpgrade`.
   Renders nothing unless `shown`. */
export function PlanLimitNotice({ shown, total, limit, plan, onUpgrade }) {
  if (!shown) return null
  const planLabel = plan ? plan[0].toUpperCase() + plan.slice(1) : 'current'
  return (
    <Banner
      tone="info"
      actions={
        <Button variant="primary" size="sm" onClick={onUpgrade}>
          Upgrade
        </Button>
      }
    >
      Showing the {limit} most recent of {total} detected signals. Your {planLabel} plan
      limits this view.
    </Banner>
  )
}
