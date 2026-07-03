import { Badge, Button, Card, ConfidenceBar, Icon } from '@verasig/design-system'
import { formatLabel } from '../../domain/template-mining/index.js'
import { ACTION_LABEL, ACTION_TONE } from './format.js'

/* Verasig — Template Mining: one template, the unit of review.
   Shows the normalized template, family stats and the accept / reject / inspect
   controls. One decision here validates or rejects every message in the
   template; "View all messages" opens the examples modal (never stretches the
   card in place). */

// Render the normalized template with <PLACEHOLDER> tokens highlighted.
function TemplateBody({ template }) {
  const parts = template.split(/(<[A-Z_]+>)/g)
  return (
    <pre className="vrs-tm-tmpl">
      {parts.map((part, index) =>
        /^<[A-Z_]+>$/.test(part) ? (
          <span key={index} className="ph">
            {part}
          </span>
        ) : (
          <span key={index}>{part}</span>
        )
      )}
    </pre>
  )
}

function dateRangeLabel(dateRange) {
  if (!dateRange) return 'No dates'
  if (dateRange.from === dateRange.to) return dateRange.from
  return `${dateRange.from} → ${dateRange.to}`
}

const STATUS_TONE = { accepted: 'verified', rejected: 'rejected' }
const STATUS_LABEL = { accepted: 'Accepted', rejected: 'Rejected' }
const STATUS_CLASS = { accepted: 'is-accepted', rejected: 'is-rejected' }

export function TemplateGroupCard({
  group,
  status,
  onAccept,
  onReject,
  onReset,
  onShowExamples
}) {
  const decidedLabel = STATUS_LABEL[status]
  const statusBadge = decidedLabel ? (
    <Badge tone={STATUS_TONE[status]} dot>
      {decidedLabel}
    </Badge>
  ) : (
    <Badge tone={ACTION_TONE[group.suggestedAction]}>
      {ACTION_LABEL[group.suggestedAction]}
    </Badge>
  )

  const cardClass = `vrs-tm-card ${STATUS_CLASS[status] || ''}`.trim()

  return (
    <Card
      title={formatLabel(group)}
      subtitle={`${group.count} messages · ${dateRangeLabel(group.dateRange)}`}
      headerActions={statusBadge}
      className={cardClass}
    >
      <TemplateBody template={group.normalizedTemplate} />

      <div className="vrs-tm-stats">
        <div>
          <div className="vrs-tm-stat__v">{group.count}</div>
          <div className="vrs-tm-stat__l">Messages</div>
        </div>
        <div className="vrs-tm-stats__bar">
          <ConfidenceBar
            value={group.confidenceAvg * 100}
            threshold={65}
            label="Avg confidence"
          />
        </div>
      </div>

      <div className="vrs-tm-actions">
        <Button
          variant={status === 'accepted' ? 'secondary' : 'primary'}
          size="sm"
          iconLeft={<Icon name="check" size={14} />}
          onClick={onAccept}
          disabled={status === 'accepted'}
        >
          Accept as signal format
        </Button>
        <Button
          variant="ghost"
          size="sm"
          iconLeft={<Icon name="x" size={14} />}
          onClick={onReject}
          disabled={status === 'rejected'}
        >
          Reject as noise/update
        </Button>
        {status !== 'unreviewed' && (
          <Button variant="ghost" size="sm" onClick={onReset}>
            Reset
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="vrs-tm-actions__expand"
          iconRight={<Icon name="search" size={14} />}
          onClick={onShowExamples}
        >
          View all {group.count} messages
        </Button>
      </div>
    </Card>
  )
}
