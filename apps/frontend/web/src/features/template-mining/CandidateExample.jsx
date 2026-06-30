import { Icon } from '@verasig/design-system'
import {
  INTENT_LABEL,
  formatConfidence,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'

/* Verasig — Template Mining: one worked example.
   The raw Telegram message beside the structured object the parser produced, plus
   any geometry / intent warnings — so a reviewer can audit the extraction itself. */
function rowClass({ muted, warning }) {
  return [muted ? 'is-muted' : null, warning ? 'is-warning' : null]
    .filter(Boolean)
    .join(' ')
}

function issueFields(candidate) {
  return new Set((candidate.parserIssues || []).map((issue) => issue.field))
}

function Row({ label, value, muted, field, warning }) {
  const className = rowClass({ muted, warning })
  return (
    <tr className={className || undefined} data-field={field}>
      <td>{label}</td>
      <td className={muted ? 'none' : undefined}>{value}</td>
    </tr>
  )
}

function IssueList({ candidate }) {
  if ((candidate.parserIssues || []).length > 0) {
    return (
      <div className="vrs-tm-issues">
        {candidate.parserIssues.map((issue) => (
          <span
            key={`${issue.code}-${issue.field}-${issue.price ?? issue.label}`}
            className="vrs-tm-warn"
          >
            <Icon name="alert" size={12} />
            <span>
              <strong>{issue.label}</strong>
              <span className="vrs-tm-warn__msg">{issue.message}</span>
            </span>
          </span>
        ))}
      </div>
    )
  }
  if (candidate.rejectionReasons.length === 0) return null
  return (
    <div className="vrs-tm-issues">
      {candidate.rejectionReasons.map((reason) => (
        <span key={reason} className="vrs-tm-warn">
          <Icon name="alert" size={12} />
          {reason}
        </span>
      ))}
    </div>
  )
}

export function CandidateExample({ candidate }) {
  const { fields } = candidate
  const takeProfits = formatTakeProfits(fields.takeProfits)
  const fieldsWithIssues = issueFields(candidate)
  return (
    <div className="vrs-tm-ex__item">
      <pre className="vrs-tm-ex__msg">{candidate.message.text}</pre>
      <div>
        <table className="vrs-tm-kv">
          <tbody>
            <Row
              label="Instrument"
              value={fields.instrument || 'none'}
              muted={!fields.instrument}
              field="instrument"
            />
            <Row
              label="Direction"
              value={fields.direction || 'none'}
              muted={!fields.direction}
              field="direction"
            />
            <Row label="Order type" value={fields.orderType} field="orderType" />
            <Row
              label="Entry"
              value={formatEntry(fields.entry)}
              muted={!fields.entry}
              field="entry"
            />
            <Row
              label="Stop loss"
              value={
                fields.stopLoss !== null && fields.stopLoss !== undefined
                  ? formatPrice(fields.stopLoss)
                  : 'none'
              }
              muted={fields.stopLoss === null || fields.stopLoss === undefined}
              field="stopLoss"
              warning={fieldsWithIssues.has('stopLoss')}
            />
            <Row
              label="Take profits"
              value={takeProfits || 'none'}
              muted={!takeProfits}
              field="takeProfits"
              warning={fieldsWithIssues.has('takeProfits')}
            />
            <Row label="Intent" value={INTENT_LABEL[candidate.intent]} field="intent" />
            <Row
              label="Confidence"
              value={formatConfidence(candidate.confidence)}
              field="confidence"
            />
          </tbody>
        </table>
        <IssueList candidate={candidate} />
      </div>
    </div>
  )
}
