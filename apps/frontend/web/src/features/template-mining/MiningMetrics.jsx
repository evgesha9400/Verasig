import { MetricStat } from '@verasig/design-system'

/* Verasig — Template Mining: headline metrics after a run.
   Shows why the approach is cheap and fast: thousands of messages collapse to a
   handful of families, and one decision per family drives full-history coverage. */
function Metric({ label, value, caption }) {
  return (
    <div className="vrs-tm-metric">
      <MetricStat label={label} value={value} caption={caption} size="sm" />
    </div>
  )
}

export function MiningMetrics({ metrics }) {
  return (
    <div className="vrs-tm-metrics">
      <Metric
        label="Messages scanned"
        value={metrics.totalMessages.toLocaleString('en-US')}
      />
      <Metric
        label="Signal candidates"
        value={metrics.candidates.toLocaleString('en-US')}
      />
      <Metric label="Families found" value={metrics.groups} />
      <Metric label="Accepted" value={metrics.accepted} caption="format families" />
      <Metric label="Rejected" value={metrics.rejected} caption="noise / updates" />
      <Metric label="Needs review" value={metrics.review} caption="undecided" />
      <Metric
        label="Signals parsed"
        value={metrics.parsedSignals.toLocaleString('en-US')}
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
