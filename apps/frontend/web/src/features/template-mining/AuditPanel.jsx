import { Badge, Card, Icon } from '@verasig/design-system'
import {
  INTENT_LABEL,
  formatConfidence,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'

/* Verasig — Template Mining: full-history audit.
   Once families are accepted, their rules run over every message and sort each
   into exactly one queue: parsed signals, ambiguous candidates, rejected
   updates/results, rare unaccepted formats, and partial-evidence misses. */
const SAMPLE_LIMIT = 4

function firstLine(text) {
  return (text || '').split('\n')[0]
}

function Queue({ icon, tone, title, count, rows }) {
  const shown = rows.slice(0, SAMPLE_LIMIT)
  return (
    <Card>
      <div className="vrs-tm-queue__head">
        <Icon name={icon} size={15} />
        <Badge tone={tone} dot aria-hidden="true" />
        <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text-strong)' }}>
          {title}
        </strong>
        <span className="vrs-tm-queue__count">{count}</span>
      </div>
      <div className="vrs-tm-queue__list">
        {shown.length === 0 ? (
          <div className="vrs-tm-source__hint">Nothing in this queue.</div>
        ) : (
          shown.map((row) => (
            <div key={row.key} className="vrs-tm-queue__row">
              {row.text}
            </div>
          ))
        )}
        {rows.length > SAMPLE_LIMIT && (
          <span className="vrs-tm-queue__more">+{rows.length - SAMPLE_LIMIT} more</span>
        )}
      </div>
    </Card>
  )
}

function signalRow(signal, index) {
  const takeProfits = formatTakeProfits(signal.takeProfits)
  const parts = [
    `${signal.instrument} ${signal.direction}`,
    `entry ${formatEntry(signal.entry)}`,
    signal.stopLoss == null ? null : `SL ${formatPrice(signal.stopLoss)}`,
    takeProfits ? `TP ${takeProfits}` : null
  ].filter(Boolean)
  return {
    key: `${signal.sourceMessageIds.join('-')}-${index}`,
    text: parts.join(' · ')
  }
}

function candidateRow(candidate, index) {
  return {
    key: `${candidate.message.id}-${index}`,
    text: `${firstLine(candidate.message.text)}  ·  ${INTENT_LABEL[candidate.intent]} ${formatConfidence(candidate.confidence)}`
  }
}

function rareRow(group, index) {
  return {
    key: `${group.templateKey}-${index}`,
    text: `${firstLine(group.normalizedTemplate)}  ·  ${group.count} message${group.count === 1 ? '' : 's'}`
  }
}

function missRow(message, index) {
  return { key: `${message.id}-${index}`, text: firstLine(message.text) }
}

export function AuditPanel({ audit, hasAccepted }) {
  if (!hasAccepted) {
    return (
      <Card title="Audit" subtitle="Run accepted rules over the full history">
        <div className="vrs-tm-source__hint">
          Accept at least one template family to run its parser over every message and
          populate the audit queues.
        </div>
      </Card>
    )
  }

  return (
    <div className="vrs-tm-audit">
      <Queue
        icon="check"
        tone="verified"
        title="Parsed signals"
        count={audit.parsedSignals.length}
        rows={audit.parsedSignals.map(signalRow)}
      />
      <Queue
        icon="alert"
        tone="pending"
        title="Ambiguous candidates"
        count={audit.ambiguousCandidates.length}
        rows={audit.ambiguousCandidates.map(candidateRow)}
      />
      <Queue
        icon="x"
        tone="rejected"
        title="Rejected updates / results"
        count={audit.rejectedCandidates.length}
        rows={audit.rejectedCandidates.map(candidateRow)}
      />
      <Queue
        icon="layers"
        tone="info"
        title="Rare / unaccepted formats"
        count={audit.rareTemplates.length}
        rows={audit.rareTemplates.map(rareRow)}
      />
      <Queue
        icon="search"
        tone="pending"
        title="Potential missed signals"
        count={audit.potentialMisses.length}
        rows={audit.potentialMisses.map(missRow)}
      />
    </div>
  )
}
