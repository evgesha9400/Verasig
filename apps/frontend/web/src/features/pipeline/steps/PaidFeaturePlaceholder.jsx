import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — upsell placeholder for the deferred post-verify routing chain
   (Exchange, Execution, Backtest). See ADR 0011. The real ExchangeView /
   ExecutionView / BacktestView are retained for the future paid-tier build. */
export function PaidFeaturePlaceholder({ feature, onDone }) {
  return (
    <div className="vrs-think vrs-think--choice vrs-fade-in" style={{ maxWidth: 560 }}>
      <span
        className="vrs-rule__ic"
        style={{ width: 64, height: 64, borderRadius: 16 }}
      >
        <Icon name="lock" size={28} />
      </span>
      <div>
        <div className="vrs-think__title">{feature} is a Pro feature</div>
        <div className="vrs-think__sub">
          Your source is verified and saved. Routing verified signals to an exchange,
          sizing execution, and backtesting are available on a higher plan — upgrade to
          unlock them.
        </div>
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
