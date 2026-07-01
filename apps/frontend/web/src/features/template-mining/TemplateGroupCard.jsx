import { useEffect, useMemo, useState } from 'react'
import { Badge, Button, Card, ConfidenceBar, Icon } from '@verasig/design-system'
import { formatLabel } from '../../domain/template-mining/index.js'
import { CandidateExample } from './CandidateExample.jsx'
import { Pager } from './Pager.jsx'
import { SignalFieldRow } from './SignalFieldRow.jsx'
import {
  ACTION_LABEL,
  ACTION_TONE,
  INTENT_LABEL,
  INTENT_ORDER,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'

/* Verasig — Template Mining: one format family, the unit of review.
   Shows the normalized template, family stats, intent mix, a representative
   extraction and the accept / reject / inspect controls. One decision here
   validates or rejects every message in the family. */

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

function IntentBar({ distribution, count }) {
  const present = INTENT_ORDER.filter((intent) => distribution[intent] > 0)
  return (
    <div>
      <div className="vrs-tm-intent">
        {present.map((intent) => (
          <span
            key={intent}
            className={`vrs-tm-intent__seg ${intent}`}
            style={{ width: `${(distribution[intent] / count) * 100}%` }}
          />
        ))}
      </div>
      <div className="vrs-tm-legend">
        {present.map((intent) => (
          <span key={intent} className="vrs-tm-legend__item">
            <span className={`vrs-tm-legend__dot vrs-tm-intent__seg ${intent}`} />
            {INTENT_LABEL[intent]} · {distribution[intent]}
          </span>
        ))}
      </div>
    </div>
  )
}

function ExtractionSummary({ candidate }) {
  const { fields } = candidate
  const takeProfits = formatTakeProfits(fields.takeProfits)
  return (
    <table className="vrs-tm-kv">
      <tbody>
        <SignalFieldRow
          label="Instrument"
          value={fields.instrument || '—'}
          field="instrument"
        />
        <SignalFieldRow
          label="Direction"
          value={fields.direction || '—'}
          field="direction"
        />
        <SignalFieldRow
          label={`Entry (${fields.orderType})`}
          value={formatEntry(fields.entry)}
          field="entry"
        />
        <SignalFieldRow
          label="Stop loss"
          value={fields.stopLoss == null ? 'none' : formatPrice(fields.stopLoss)}
          muted={fields.stopLoss == null}
          field="stopLoss"
        />
        <SignalFieldRow
          label="Take profits"
          value={takeProfits || 'none'}
          muted={!takeProfits}
          field="takeProfits"
        />
      </tbody>
    </table>
  )
}

function dateRangeLabel(dateRange) {
  if (!dateRange) return 'No dates'
  if (dateRange.from === dateRange.to) return dateRange.from
  return `${dateRange.from} → ${dateRange.to}`
}

// Reviewers page through EVERY message in the family — five at a time — to
// double-check the grouping, not just the top-confidence examples.
const MESSAGES_PER_PAGE = 5

const STATUS_TONE = { accepted: 'verified', rejected: 'rejected' }
const STATUS_LABEL = { accepted: 'Accepted', rejected: 'Rejected' }
const STATUS_CLASS = { accepted: 'is-accepted', rejected: 'is-rejected' }

export function TemplateGroupCard({
  group,
  status,
  expanded,
  onAccept,
  onReject,
  onReset,
  onToggleExamples
}) {
  const [page, setPage] = useState(0)

  // Collapsing the list returns it to the first page for next time.
  useEffect(() => {
    if (!expanded) setPage(0)
  }, [expanded])

  // Highest-confidence first, so page one leads with the same representative the
  // summary above shows and the cleanest examples come first. Only worth sorting
  // once the reviewer actually expands the family — most cards never are.
  const ordered = useMemo(
    () =>
      expanded ? [...group.candidates].sort((a, b) => b.confidence - a.confidence) : [],
    [group.candidates, expanded]
  )
  const total = ordered.length
  const pageCount = Math.max(1, Math.ceil(total / MESSAGES_PER_PAGE))
  const safePage = Math.min(page, pageCount - 1)
  const windowStart = safePage * MESSAGES_PER_PAGE
  const pageItems = ordered.slice(windowStart, windowStart + MESSAGES_PER_PAGE)

  const representative = group.examples[0]
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

      <IntentBar distribution={group.intentDistribution} count={group.count} />

      {group.geometryWarnings > 0 && (
        <span className="vrs-tm-warn">
          <Icon name="alert" size={12} />
          {group.geometryWarnings} of {group.count} have suspicious stop/target geometry
        </span>
      )}

      <ExtractionSummary candidate={representative} />

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
          iconRight={<Icon name={expanded ? 'arrowUp' : 'arrowDown'} size={14} />}
          onClick={onToggleExamples}
        >
          {expanded ? 'Hide messages' : `Show all ${group.count} messages`}
        </Button>
      </div>

      {expanded && (
        <div className="vrs-tm-ex">
          {pageItems.map((candidate) => (
            <CandidateExample key={candidate.message.id} candidate={candidate} />
          ))}
          <Pager
            page={safePage}
            pageCount={pageCount}
            windowStart={windowStart}
            pageSize={MESSAGES_PER_PAGE}
            total={total}
            onPageChange={setPage}
          />
        </div>
      )}
    </Card>
  )
}
