import { useEffect, useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Checkbox,
  Icon,
  Input,
  Loader,
  Select,
  Tabs
} from '@verasig/design-system'
import { Pager } from '../../shared/components/Pager.jsx'
import { PlanLimitNotice } from '../../shared/components/PlanLimitNotice.jsx'
import { signalLimitFor } from '../../domain/plan/planLimits.js'
import {
  INTENT_LABEL,
  byCoverageThenConfidence,
  byMessageDateDesc,
  formatConfidence,
  formatEntry,
  formatMessageDate,
  formatPrice,
  formatTakeProfits
} from './format.js'
import { CandidateExample } from './CandidateExample.jsx'
import { SignalFieldRow } from './SignalFieldRow.jsx'
import { toggleInSet } from './toggleSet.js'

/* Verasig — Template Mining: full-history result review.
   Once families are accepted and their rules run over every message, this is
   where a reviewer scans the outcome: a tab per audit bucket, a free-text
   search, and a filter-by-template Select. One paginated, filterable list
   replaces the five capped preview cards. Pure presentation over the audit
   result + the raw messages (parsed signals carry ids, not text). */

const PAGE_SIZE = 25

// Buckets that came from an accepted template can be narrowed by the template
// Select; the rest (updates/results, rare formats, misses) cannot.
const TABS = [
  { id: 'parsed', label: 'Parsed', templated: true },
  { id: 'ambiguous', label: 'Ambiguous', templated: true },
  { id: 'rejected', label: 'Rejected', templated: false },
  { id: 'rare', label: 'Rare', templated: false },
  { id: 'misses', label: 'Misses', templated: false }
]

function firstLine(text) {
  return (text || '').split('\n')[0]
}

function issueSummary(candidate) {
  const issues = candidate.parserIssues || []
  if (issues.length === 0) return null
  return {
    kind: 'Price geometry issue',
    label: issues.map((issue) => issue.label).join(', ')
  }
}

const confidenceOf = (row) => row.confidence

// Compose two comparators: the secondary only breaks ties the primary left at 0.
const thenBy = (primary, secondary) => (a, b) => primary(a, b) || secondary(a, b)

// Each row is { key, text, template?, templateId?, haystack } — one shape so a
// single search/filter path serves every bucket. The row whose template parsed
// the most messages in this backtest leads (most-likely template first), then
// confidence within a template — matches the family grid and compiled-rules order.
function parsedRows(signals, messageById, templateById, countByRule) {
  const coverageOf = (signal) => countByRule.get(signal.parserRuleId) || 0
  const dateOf = (signal) => messageById.get(signal.sourceMessageIds[0])?.date
  return [...signals]
    .sort(
      thenBy(
        byMessageDateDesc(dateOf),
        byCoverageThenConfidence(coverageOf, confidenceOf)
      )
    )
    .map((signal, index) => {
      const takeProfits = formatTakeProfits(signal.takeProfits)
      const text = [
        `${signal.instrument} ${signal.direction}`,
        `entry ${formatEntry(signal.entry)}`,
        signal.stopLoss == null ? null : `SL ${formatPrice(signal.stopLoss)}`,
        takeProfits ? `TP ${takeProfits}` : null
      ]
        .filter(Boolean)
        .join(' · ')
      const sourceMessage = messageById.get(signal.sourceMessageIds[0])
      const sourceText = sourceMessage?.text || ''
      const template = templateById.get(signal.parserRuleId)
      return {
        key: `${signal.sourceMessageIds.join('-')}-${index}`,
        text,
        template: template?.name,
        templateId: signal.parserRuleId,
        // Recovered by a general family it does not exactly match — flag it so the
        // reviewer can scrutinize looser matches without leaving the Parsed bucket.
        fallback: signal.match === 'fallback',
        haystack:
          `${text} ${signal.instrument} ${signal.direction} ${sourceText}`.toLowerCase(),
        detail: {
          kind: 'parsed',
          signal,
          messageText: sourceText,
          messageDate: sourceMessage?.date,
          template: template?.name
        }
      }
    })
}

function ambiguousRows(candidates, templateIdByTemplateKey, countByRule) {
  const coverageOf = (candidate) =>
    countByRule.get(templateIdByTemplateKey.get(candidate.templateKey)) || 0
  const dateOf = (candidate) => candidate.message.date
  return [...candidates]
    .sort(
      thenBy(
        byMessageDateDesc(dateOf),
        byCoverageThenConfidence(coverageOf, confidenceOf)
      )
    )
    .map((candidate, index) => {
      const issue = issueSummary(candidate)
      const text = `${firstLine(candidate.message.text)}  ·  ${INTENT_LABEL[candidate.intent]} ${formatConfidence(candidate.confidence)}`
      return {
        key: `${candidate.message.id}-${index}`,
        text,
        issue,
        templateId: templateIdByTemplateKey.get(candidate.templateKey),
        haystack:
          `${candidate.message.text} ${INTENT_LABEL[candidate.intent]} ${issue?.kind || ''} ${issue?.label || ''}`.toLowerCase(),
        detail: { kind: 'candidate', candidate }
      }
    })
}

// The rejected/rare/miss buckets share one row shape — only how each item
// supplies its key/summary/search text/detail text differs.
function textRows(items, { keyOf, textOf, haystackOf, messageTextOf, messageDateOf }) {
  return items.map((item, index) => ({
    key: `${keyOf(item)}-${index}`,
    text: textOf(item),
    templateId: null,
    haystack: haystackOf(item).toLowerCase(),
    detail: {
      kind: 'text',
      messageText: messageTextOf(item),
      messageDate: messageDateOf(item)
    }
  }))
}

function rejectedRows(entries) {
  return textRows([...entries].sort(byMessageDateDesc((entry) => entry.message.date)), {
    keyOf: (entry) => entry.message.id,
    textOf: (entry) =>
      `${firstLine(entry.message.text)}  ·  ${INTENT_LABEL[entry.intent]}`,
    haystackOf: (entry) => `${entry.message.text} ${INTENT_LABEL[entry.intent]}`,
    messageTextOf: (entry) => entry.message.text,
    messageDateOf: (entry) => entry.message.date
  })
}

function rareRows(groups) {
  return textRows(groups, {
    keyOf: (group) => group.templateKey,
    textOf: (group) =>
      `${firstLine(group.normalizedTemplate)}  ·  ${group.count} message${group.count === 1 ? '' : 's'}`,
    haystackOf: (group) => group.normalizedTemplate,
    messageTextOf: (group) => group.normalizedTemplate,
    // A rare template is a group, not one message — no per-message date to show.
    messageDateOf: () => null
  })
}

function missRows(messages) {
  return textRows([...messages].sort(byMessageDateDesc((message) => message.date)), {
    keyOf: (message) => message.id,
    textOf: (message) => firstLine(message.text),
    haystackOf: (message) => message.text || '',
    messageTextOf: (message) => message.text,
    messageDateOf: (message) => message.date
  })
}

// A parsed row expands to the original message beside the structured fields;
// every other row expands to its full original text.
function RowDetail({ detail }) {
  if (detail.kind === 'candidate') {
    return <CandidateExample candidate={detail.candidate} />
  }
  if (detail.kind !== 'parsed') {
    return (
      <>
        {detail.messageDate && (
          <div className="vrs-tm-ex__date">{formatMessageDate(detail.messageDate)}</div>
        )}
        <pre className="vrs-tm-ex__msg">{detail.messageText || '—'}</pre>
      </>
    )
  }
  const signal = detail.signal
  const takeProfits = formatTakeProfits(signal.takeProfits)
  return (
    <div className="vrs-tm-ex__item">
      <div>
        {detail.messageDate && (
          <div className="vrs-tm-ex__date">{formatMessageDate(detail.messageDate)}</div>
        )}
        <pre className="vrs-tm-ex__msg">
          {detail.messageText || '— original message unavailable —'}
        </pre>
      </div>
      <table className="vrs-tm-kv">
        <tbody>
          <SignalFieldRow
            label="Instrument"
            value={signal.instrument || '—'}
            field="instrument"
          />
          <SignalFieldRow
            label="Direction"
            value={signal.direction}
            field="direction"
          />
          <SignalFieldRow
            label={`Entry (${signal.orderType})`}
            value={formatEntry(signal.entry)}
            field="entry"
          />
          <SignalFieldRow
            label="Stop loss"
            value={signal.stopLoss == null ? 'none' : formatPrice(signal.stopLoss)}
            muted={signal.stopLoss == null}
            field="stopLoss"
          />
          <SignalFieldRow
            label="Take profits"
            value={takeProfits || 'none'}
            muted={!takeProfits}
            field="takeProfits"
          />
          <SignalFieldRow
            label="Confidence"
            value={formatConfidence(signal.confidence)}
            field="confidence"
          />
          {detail.template && (
            <SignalFieldRow label="Template" value={detail.template} field="template" />
          )}
        </tbody>
      </table>
    </div>
  )
}

function ReviewHead({ subtitle, actions }) {
  return (
    <div className="vrs-tm-section__head">
      <div>
        <div className="vrs-tm-section__title">Review results</div>
        <div className="vrs-tm-section__sub">{subtitle}</div>
      </div>
      {actions && <div className="vrs-tm-bulk">{actions}</div>}
    </div>
  )
}

export function AuditReview({
  audit,
  messages = [],
  templates = [],
  hasAccepted,
  loading = false,
  error = null,
  plan,
  onUpgrade,
  onFinish,
  onKeepVerified
}) {
  const [tab, setTab] = useState('parsed')
  const [query, setQuery] = useState('')
  const [templateId, setTemplateId] = useState('all')
  const [page, setPage] = useState(0)
  const [openKeys, setOpenKeys] = useState(() => new Set())

  function toggleRow(key) {
    setOpenKeys((current) => toggleInSet(current, key))
  }

  const messageById = useMemo(
    () => new Map(messages.map((message) => [message.id, message])),
    [messages]
  )
  const templateById = useMemo(
    () => new Map(templates.map((template) => [template.id, template])),
    [templates]
  )
  const templateIdByTemplateKey = useMemo(
    () => new Map(templates.map((template) => [template.templateKey, template.id])),
    [templates]
  )

  // How many signals each accepted template parsed in this backtest — its
  // coverage. Drives both the parsed-row ordering (most-covering family first)
  // and the template-filter labels (several families can share one display name).
  const parsedCountByTemplate = useMemo(() => {
    const counts = new Map()
    for (const signal of audit.parsedSignals) {
      counts.set(signal.parserRuleId, (counts.get(signal.parserRuleId) || 0) + 1)
    }
    return counts
  }, [audit])

  // Tab badges only need a count per bucket, not its fully built (and sorted,
  // formatted) rows — so they read the raw audit arrays directly.
  const tabCounts = {
    parsed: audit.parsedSignals.length,
    ambiguous: audit.ambiguousCandidates.length,
    rejected: audit.rejectedCandidates.length,
    rare: audit.rareTemplates.length,
    misses: audit.potentialMisses.length
  }

  // Only the active tab's rows are ever rendered, so only build that bucket.
  const activeRows = useMemo(() => {
    if (tab === 'parsed') {
      return parsedRows(
        audit.parsedSignals,
        messageById,
        templateById,
        parsedCountByTemplate
      )
    }
    if (tab === 'ambiguous') {
      return ambiguousRows(
        audit.ambiguousCandidates,
        templateIdByTemplateKey,
        parsedCountByTemplate
      )
    }
    if (tab === 'rejected') return rejectedRows(audit.rejectedCandidates)
    if (tab === 'rare') return rareRows(audit.rareTemplates)
    return missRows(audit.potentialMisses)
  }, [
    tab,
    audit,
    messageById,
    templateById,
    templateIdByTemplateKey,
    parsedCountByTemplate
  ])

  const activeTab = TABS.find((entry) => entry.id === tab)
  const templateEnabled = activeTab.templated && templates.length > 0
  const effectiveTemplate = templateEnabled ? templateId : 'all'

  // Observer cap: only the N most-recent parsed signals are the observer's — the
  // same value limit the Signals page enforces. parsedRows is already date-desc,
  // so slice the head. Other buckets are not "signals" and stay uncapped.
  const signalLimit = signalLimitFor(plan)
  const parsedTotal = tab === 'parsed' ? activeRows.length : 0
  const limitReached =
    tab === 'parsed' && signalLimit != null && parsedTotal > signalLimit
  const visibleRows = limitReached ? activeRows.slice(0, signalLimit) : activeRows

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return visibleRows.filter(
      (row) =>
        (!needle || row.haystack.includes(needle)) &&
        (effectiveTemplate === 'all' || row.templateId === effectiveTemplate)
    )
  }, [visibleRows, query, effectiveTemplate])

  // Any filter change returns the list to the first page.
  useEffect(() => {
    setPage(0)
  }, [tab, query, effectiveTemplate])

  if (!hasAccepted) {
    return (
      <section className="vrs-tm-review">
        <ReviewHead subtitle="Run the accepted rules over the full history" />
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">
            Accept at least one template family to run its parser over every message and
            populate the review.
          </div>
        </div>
      </section>
    )
  }

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const windowStart = safePage * PAGE_SIZE
  const pageRows = filtered.slice(windowStart, windowStart + PAGE_SIZE)

  // "Expand all" toggles every row across the whole filtered set (so paging keeps
  // them open), and reflects whether they are all currently open.
  const allOpen = filtered.length > 0 && filtered.every((row) => openKeys.has(row.key))
  const toggleAll = (checked) =>
    setOpenKeys(checked ? new Set(filtered.map((row) => row.key)) : new Set())

  const templateOptions = [
    { value: 'all', label: 'All templates' },
    ...templates.map((template) => ({
      value: template.id,
      label: `${template.name} · ${parsedCountByTemplate.get(template.id) || 0} parsed`
    }))
  ]
  const tabItems = TABS.map((entry) => ({
    id: entry.id,
    label: entry.label,
    count: tabCounts[entry.id]
  }))

  return (
    <section className="vrs-tm-review">
      <ReviewHead
        subtitle={
          loading
            ? 'Refreshing the audit for your latest template decisions…'
            : 'Search and filter every message the parser sorted'
        }
        actions={
          <>
            {onKeepVerified && (
              <Button variant="primary" size="sm" onClick={onKeepVerified}>
                Keep verified
              </Button>
            )}
            <Button variant="secondary" size="sm" onClick={onFinish}>
              Confirm &amp; route to Exchange
            </Button>
          </>
        }
      />

      {error && (
        <div className="vrs-empty vrs-empty--sm" role="alert">
          <div className="vrs-empty__note">
            Couldn&apos;t refresh the audit. {error}
          </div>
        </div>
      )}

      <div className="vrs-tm-review__bar">
        <div className="vrs-tm-review__filters">
          <Input
            label="Search"
            placeholder="Search results…"
            value={query}
            aria-label="Search results"
            iconLeft={<Icon name="search" size={16} />}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Select
            label="Template"
            value={effectiveTemplate}
            disabled={!templateEnabled}
            options={templateOptions}
            onChange={(event) => setTemplateId(event.target.value)}
          />
        </div>
        <div className="vrs-tm-review__count">
          <span className="vrs-tm-review__count-v">{filtered.length}</span>
          <span className="vrs-tm-review__count-l">
            {filtered.length === 1 ? 'result' : 'results'}
          </span>
        </div>
      </div>

      <div className="vrs-tm-review__tabsrow">
        <Tabs value={tab} onChange={setTab} items={tabItems} />
        <Checkbox
          label="Expand all"
          checked={allOpen}
          onChange={(event) => toggleAll(event.target.checked)}
        />
      </div>

      {/* Parsed-tab only: the observer's most-recent-N signal cap. */}
      <PlanLimitNotice
        shown={limitReached}
        total={parsedTotal}
        limit={signalLimit}
        plan={plan}
        onUpgrade={onUpgrade}
      />

      {loading ? (
        <Loader variant="bar" size="sm" title="Refreshing the audit…" />
      ) : pageRows.length === 0 ? (
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">No results match your filters.</div>
        </div>
      ) : (
        <div className="vrs-tm-review__list">
          {pageRows.map((row) => {
            const open = openKeys.has(row.key)
            return (
              <div key={row.key} className="vrs-tm-review__item">
                <button
                  type="button"
                  className="vrs-tm-review__row"
                  aria-expanded={open}
                  onClick={() => toggleRow(row.key)}
                >
                  <span className="vrs-tm-review__chev">
                    <Icon name={open ? 'arrowUp' : 'arrowDown'} size={13} />
                  </span>
                  <span className="vrs-tm-review__row-text" title={row.text}>
                    {row.text}
                  </span>
                  {row.fallback && (
                    <span className="vrs-tm-review__flag">
                      <Badge tone="info">fallback</Badge>
                    </span>
                  )}
                  {row.template && (
                    <span className="vrs-tm-review__tmpl" title={row.template}>
                      {row.template}
                    </span>
                  )}
                  {row.issue && (
                    <>
                      <span className="vrs-tm-review__issue">
                        <Icon name="alert" size={12} />
                        {row.issue.kind}
                      </span>
                      <span
                        className="vrs-tm-review__issue-label"
                        title={row.issue.label}
                      >
                        {row.issue.label}
                      </span>
                    </>
                  )}
                </button>
                {open && (
                  <div className="vrs-tm-review__detail">
                    <RowDetail detail={row.detail} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <Pager
        page={safePage}
        pageCount={pageCount}
        windowStart={windowStart}
        pageSize={PAGE_SIZE}
        total={filtered.length}
        onPageChange={setPage}
      />
    </section>
  )
}

export default AuditReview
