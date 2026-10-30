import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — placeholder for the post-verify routing chain (Exchange, Backtest,
   Execution). Two reasons a step lands here: it's beyond the user's plan
   (upgrade), or it's within reach but not built yet (coming soon). The real
   engines arrive in the deferred build. */
export function PaidFeaturePlaceholder({
  feature,
  planName = 'Trader',
  lockedByPlan = true,
  onDone
}) {
  const title = lockedByPlan
    ? `${feature} is a ${planName} feature`
    : `${feature} is coming soon`
  const blurb = lockedByPlan
    ? `Your source is verified and saved. ${feature} is available on the ${planName} plan — upgrade to unlock it.`
    : 'Your source is verified and saved. This step is on the way — it isn’t available to configure just yet.'
  return (
    <div className="vrs-think vrs-think--choice vrs-fade-in" style={{ maxWidth: 560 }}>
      <span
        className="vrs-rule__ic"
        style={{ width: 64, height: 64, borderRadius: 16 }}
      >
        <Icon name="lock" size={28} />
      </span>
      <div>
        <div className="vrs-think__title">{title}</div>
        <div className="vrs-think__sub">{blurb}</div>
      </div>
      <Button
        variant="primary"
        size="lg"
        iconLeft={<Icon name="arrowLeft" size={16} />}
        onClick={onDone}
      >
        Back to feeds
      </Button>
    </div>
  )
}
