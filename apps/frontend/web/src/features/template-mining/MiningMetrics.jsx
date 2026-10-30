import { MetricStat } from '@verasig/design-system'

/* Verasig — Template Mining metrics.
   Shows why the approach is cheap and fast: thousands of messages collapse to a
   handful of templates, and one decision per template drives full coverage. The
   `slim` variant is the review-focused subset shown on the Review sub-step. */
function Metric({ label, value, caption }) {
  return (
    <div className="vrs-tm-metric">
      <MetricStat label={label} value={value} caption={caption} size="sm" />
    </div>
  )
}

const NUM = (value) => value.toLocaleString('en-US')

export function MiningMetrics({ metrics, variant = 'full' }) {
  if (variant === 'slim') {
    return (
      <div className="vrs-tm-metrics vrs-tm-metrics--slim">
        <Metric label="Messages scanned" value={NUM(metrics.totalMessages)} />
        <Metric label="Templates" value={metrics.groups} caption="distinct formats" />
        <Metric label="Accepted" value={metrics.accepted} caption="templates" />
        <Metric label="Needs review" value={metrics.review} caption="undecided" />
      </div>
    )
  }
  return (
    <div className="vrs-tm-metrics">
      <Metric
        label="Messages scanned"
        value={NUM(metrics.totalMessages)}
        caption="in this source"
      />
      <Metric
        label="Signal candidates"
        value={NUM(metrics.candidates)}
        caption="parsed as signals"
      />
      <Metric
        label="Templates found"
        value={metrics.groups}
        caption="distinct formats"
      />
      <Metric label="Accepted" value={metrics.accepted} caption="templates" />
      <Metric label="Rejected" value={metrics.rejected} caption="noise / updates" />
      <Metric label="Needs review" value={metrics.review} caption="undecided" />
      <Metric
        label="Signals parsed"
        value={NUM(metrics.parsedSignals)}
        caption="from accepted rules"
      />
      <Metric
        label="Candidate coverage"
        value={metrics.coverage}
        caption="of candidates parsed"
      />
    </div>
  )
}
