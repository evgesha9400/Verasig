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
function Row({ label, value, muted }) {
  return (
    <tr>
      <td>{label}</td>
      <td className={muted ? 'none' : undefined}>{value}</td>
    </tr>
  )
}

export function CandidateExample({ candidate }) {
  const { fields } = candidate
  const takeProfits = formatTakeProfits(fields.takeProfits)
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
            />
            <Row
              label="Direction"
              value={fields.direction || 'none'}
              muted={!fields.direction}
            />
            <Row label="Order type" value={fields.orderType} />
            <Row
              label="Entry"
              value={formatEntry(fields.entry)}
              muted={!fields.entry}
            />
            <Row
              label="Stop loss"
              value={
                fields.stopLoss !== null && fields.stopLoss !== undefined
                  ? formatPrice(fields.stopLoss)
                  : 'none'
              }
              muted={fields.stopLoss === null || fields.stopLoss === undefined}
            />
            <Row
              label="Take profits"
              value={takeProfits || 'none'}
              muted={!takeProfits}
            />
            <Row label="Intent" value={INTENT_LABEL[candidate.intent]} />
            <Row label="Confidence" value={formatConfidence(candidate.confidence)} />
          </tbody>
        </table>
        {candidate.rejectionReasons.length > 0 && (
          <div
            style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}
          >
            {candidate.rejectionReasons.map((reason) => (
              <span key={reason} className="vrs-tm-warn">
                <Icon name="alert" size={12} />
                {reason}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
