import { useEffect, useMemo, useState } from 'react'
import { Badge, Checkbox, Icon, Input, Select, Tabs } from '@verasig/design-system'
import { byCoverageThenConfidence } from '../../domain/template-mining/index.js'
import { Pager } from './Pager.jsx'
import {
  INTENT_LABEL,
  formatConfidence,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'
import { CandidateExample } from './CandidateExample.jsx'
import { SignalFieldRow } from './SignalFieldRow.jsx'

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

// Each row is { key, text, template?, templateId?, haystack } — one shape so a
// single search/filter path serves every bucket. The row whose template parsed
// the most messages in this backtest leads (most-likely template first), then
// confidence within a template — matches the family grid and compiled-rules order.
function parsedRows(signals, messageById, ruleById, countByRule) {
  const coverageOf = (signal) => countByRule.get(signal.parserRuleId) || 0
  return [...signals]
    .sort(byCoverageThenConfidence(coverageOf, confidenceOf))
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
      const sourceText = messageById.get(signal.sourceMessageIds[0])?.text || ''
      const rule = ruleById.get(signal.parserRuleId)
      return {
        key: `${signal.sourceMessageIds.join('-')}-${index}`,
        text,
        template: rule?.name,
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
          template: rule?.name
        }
      }
    })
}

function ambiguousRows(candidates, ruleByTemplateKey, countByRule) {
  const coverageOf = (candidate) =>
    countByRule.get(ruleByTemplateKey.get(candidate.templateKey)) || 0
  return [...candidates]
    .sort(byCoverageThenConfidence(coverageOf, confidenceOf))
    .map((candidate, index) => {
      const issue = issueSummary(candidate)
      const text = `${firstLine(candidate.message.text)}  ·  ${INTENT_LABEL[candidate.intent]} ${formatConfidence(candidate.confidence)}`
      return {
        key: `${candidate.message.id}-${index}`,
        text,
        issue,
        templateId: ruleByTemplateKey.get(candidate.templateKey),
        haystack:
          `${candidate.message.text} ${INTENT_LABEL[candidate.intent]} ${issue?.kind || ''} ${issue?.label || ''}`.toLowerCase(),
        detail: { kind: 'candidate', candidate }
      }
    })
}

// The rejected/rare/miss buckets share one row shape — only how each item
// supplies its key/summary/search text/detail text differs.
function textRows(items, { keyOf, textOf, haystackOf, messageTextOf }) {
  return items.map((item, index) => ({
    key: `${keyOf(item)}-${index}`,
    text: textOf(item),
    templateId: null,
    haystack: haystackOf(item).toLowerCase(),
    detail: { kind: 'text', messageText: messageTextOf(item) }
  }))
}

function rejectedRows(entries) {
  return textRows(entries, {
    keyOf: (entry) => entry.message.id,
    textOf: (entry) =>
      `${firstLine(entry.message.text)}  ·  ${INTENT_LABEL[entry.intent]}`,
    haystackOf: (entry) => `${entry.message.text} ${INTENT_LABEL[entry.intent]}`,
    messageTextOf: (entry) => entry.message.text
  })
}

function rareRows(groups) {
  return textRows(groups, {
    keyOf: (group) => group.templateKey,
    textOf: (group) =>
      `${firstLine(group.normalizedTemplate)}  ·  ${group.count} message${group.count === 1 ? '' : 's'}`,
    haystackOf: (group) => group.normalizedTemplate,
    messageTextOf: (group) => group.normalizedTemplate
  })
}

function missRows(messages) {
  return textRows(messages, {
    keyOf: (message) => message.id,
    textOf: (message) => firstLine(message.text),
    haystackOf: (message) => message.text || '',
    messageTextOf: (message) => message.text
  })
}

// A parsed row expands to the original message beside the structured fields;
// every other row expands to its full original text.
function RowDetail({ detail }) {
  if (detail.kind === 'candidate') {
    return <CandidateExample candidate={detail.candidate} />
  }
  if (detail.kind !== 'parsed') {
    return <pre className="vrs-tm-ex__msg">{detail.messageText || '—'}</pre>
  }
  const signal = detail.signal
  const takeProfits = formatTakeProfits(signal.takeProfits)
  return (
    <div className="vrs-tm-ex__item">
      <pre className="vrs-tm-ex__msg">
        {detail.messageText || '— original message unavailable —'}
      </pre>
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

function ReviewHead({ subtitle }) {
  return (
    <div className="vrs-tm-section__head">
      <div>
        <div className="vrs-tm-section__title">Review results</div>
        <div className="vrs-tm-section__sub">{subtitle}</div>
      </div>
    </div>
  )
}

export function AuditReview({ audit, messages = [], rules = [], hasAccepted }) {
  const [tab, setTab] = useState('parsed')
  const [query, setQuery] = useState('')
  const [templateId, setTemplateId] = useState('all')
  const [page, setPage] = useState(0)
  const [openKeys, setOpenKeys] = useState(() => new Set())

  function toggleRow(key) {
    setOpenKeys((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const messageById = useMemo(
    () => new Map(messages.map((message) => [message.id, message])),
    [messages]
  )
  const ruleById = useMemo(() => new Map(rules.map((rule) => [rule.id, rule])), [rules])
  const ruleByTemplateKey = useMemo(
    () => new Map(rules.map((rule) => [rule.templateKey, rule.id])),
    [rules]
  )

  // How many signals each accepted rule parsed in this backtest — its coverage.
  // Drives both the parsed-row ordering (most-covering family first) and the
  // template-filter labels (several families can share one display name).
  const parsedCountByRule = useMemo(() => {
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
      return parsedRows(audit.parsedSignals, messageById, ruleById, parsedCountByRule)
    }
    if (tab === 'ambiguous') {
      return ambiguousRows(
        audit.ambiguousCandidates,
        ruleByTemplateKey,
        parsedCountByRule
      )
    }
    if (tab === 'rejected') return rejectedRows(audit.rejectedCandidates)
    if (tab === 'rare') return rareRows(audit.rareTemplates)
    return missRows(audit.potentialMisses)
  }, [tab, audit, messageById, ruleById, ruleByTemplateKey, parsedCountByRule])

  const activeTab = TABS.find((entry) => entry.id === tab)
  const templateEnabled = activeTab.templated && rules.length > 0
  const effectiveTemplate = templateEnabled ? templateId : 'all'

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return activeRows.filter(
      (row) =>
        (!needle || row.haystack.includes(needle)) &&
        (effectiveTemplate === 'all' || row.templateId === effectiveTemplate)
    )
  }, [activeRows, query, effectiveTemplate])

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
    ...rules.map((rule) => ({
      value: rule.id,
      label: `${rule.name} · ${parsedCountByRule.get(rule.id) || 0} parsed`
    }))
  ]
  const tabItems = TABS.map((entry) => ({
    id: entry.id,
    label: entry.label,
    count: tabCounts[entry.id]
  }))

  return (
    <section className="vrs-tm-review">
      <ReviewHead subtitle="Search and filter every message the parser sorted" />

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

      {pageRows.length === 0 ? (
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
