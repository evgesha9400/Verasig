import { useEffect, useState } from 'react'
import { Button, Dialog, Icon } from '@verasig/design-system'
import { formatLabel } from './templateLabel.js'
import { CandidateExample } from './CandidateExample.jsx'
import { Pager } from '../../shared/components/Pager.jsx'
import { SignalFieldRow } from './SignalFieldRow.jsx'
import {
  INTENT_LABEL,
  INTENT_ORDER,
  byMessageDateDesc,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'

/* Verasig — Template Mining: every message in one template, in a modal.
   Opening this replaced expanding the card in place (which stretched the grid).
   The reviewer can page through all examples and accept/reject without leaving. */

const MESSAGES_PER_PAGE = 5

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

export function TemplateExamplesDialog({
  group,
  open,
  onClose,
  status,
  onAccept,
  onReject,
  onReset
}) {
  const [page, setPage] = useState(0)

  // A different template starts over at the first page: the previous group's
  // page index could point past the new group's pages.
  useEffect(() => {
    setPage(0)
  }, [group?.templateKey])

  if (!open || !group) return null

  const ordered = [...group.candidates].sort(
    byMessageDateDesc((candidate) => candidate.message.date)
  )
  const total = ordered.length
  const pageCount = Math.max(1, Math.ceil(total / MESSAGES_PER_PAGE))
  const safePage = Math.min(page, pageCount - 1)
  const windowStart = safePage * MESSAGES_PER_PAGE
  const pageItems = ordered.slice(windowStart, windowStart + MESSAGES_PER_PAGE)

  const footer = (
    <>
      {status !== 'unreviewed' && (
        <Button variant="ghost" size="sm" onClick={onReset}>
          Reset
        </Button>
      )}
      <Button
        variant="ghost"
        size="sm"
        iconLeft={<Icon name="x" size={14} />}
        onClick={onReject}
        disabled={status === 'rejected'}
      >
        Reject
      </Button>
      <Button
        variant="primary"
        size="sm"
        iconLeft={<Icon name="check" size={14} />}
        onClick={onAccept}
        disabled={status === 'accepted'}
      >
        Accept
      </Button>
    </>
  )

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={formatLabel(group)}
      description={`${group.count} messages`}
      className="vrs-tm-exdialog"
      footer={footer}
    >
      <IntentBar distribution={group.intentDistribution} count={group.count} />

      {group.geometryWarnings > 0 && (
        <span className="vrs-tm-warn">
          <Icon name="alert" size={12} />
          {group.geometryWarnings} of {group.count} have suspicious stop/target geometry
        </span>
      )}

      {group.examples[0] && <ExtractionSummary candidate={group.examples[0]} />}

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
    </Dialog>
  )
}
