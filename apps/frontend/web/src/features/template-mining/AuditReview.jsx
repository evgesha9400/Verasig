import { useEffect, useMemo, useState } from 'react'
import { Checkbox, Icon, Input, Select, Tabs } from '@verasig/design-system'
import { Pager } from './Pager.jsx'
import {
  INTENT_LABEL,
  formatConfidence,
  formatEntry,
  formatPrice,
  formatTakeProfits
} from './format.js'

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

// Each row is { key, text, template?, templateId?, haystack } — one shape so a
// single search/filter path serves every bucket.
function parsedRows(signals, messageById, ruleById) {
  return signals.map((signal, index) => {
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
      haystack:
        `${text} ${signal.instrument} ${signal.direction} ${sourceText}`.toLowerCase(),
      detail: { kind: 'parsed', signal, messageText: sourceText, template: rule?.name }
    }
  })
}

function ambiguousRows(candidates, ruleByTemplateKey) {
  return candidates.map((candidate, index) => {
    const text = `${firstLine(candidate.message.text)}  ·  ${INTENT_LABEL[candidate.intent]} ${formatConfidence(candidate.confidence)}`
    return {
      key: `${candidate.message.id}-${index}`,
      text,
      templateId: ruleByTemplateKey.get(candidate.templateKey),
      haystack:
        `${candidate.message.text} ${INTENT_LABEL[candidate.intent]}`.toLowerCase(),
      detail: { kind: 'text', messageText: candidate.message.text }
    }
  })
}

function rejectedRows(entries) {
  return entries.map((entry, index) => ({
    key: `${entry.message.id}-${index}`,
    text: `${firstLine(entry.message.text)}  ·  ${INTENT_LABEL[entry.intent]}`,
    templateId: null,
    haystack: `${entry.message.text} ${INTENT_LABEL[entry.intent]}`.toLowerCase(),
    detail: { kind: 'text', messageText: entry.message.text }
  }))
}

function rareRows(groups) {
  return groups.map((group, index) => ({
    key: `${group.templateKey}-${index}`,
    text: `${firstLine(group.normalizedTemplate)}  ·  ${group.count} message${group.count === 1 ? '' : 's'}`,
    templateId: null,
    haystack: group.normalizedTemplate.toLowerCase(),
    detail: { kind: 'text', messageText: group.normalizedTemplate }
  }))
}

function missRows(messages) {
  return messages.map((message, index) => ({
    key: `${message.id}-${index}`,
    text: firstLine(message.text),
    templateId: null,
    haystack: (message.text || '').toLowerCase(),
    detail: { kind: 'text', messageText: message.text }
  }))
}

// A parsed row expands to the original message beside the structured fields;
// every other row expands to its full original text.
function RowDetail({ detail }) {
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
          <tr>
            <td>Instrument</td>
            <td>{signal.instrument || '—'}</td>
          </tr>
          <tr>
            <td>Direction</td>
            <td>{signal.direction}</td>
          </tr>
          <tr>
            <td>Entry ({signal.orderType})</td>
            <td>{formatEntry(signal.entry)}</td>
          </tr>
          <tr>
            <td>Stop loss</td>
            <td className={signal.stopLoss == null ? 'none' : undefined}>
              {signal.stopLoss == null ? 'none' : formatPrice(signal.stopLoss)}
            </td>
          </tr>
          <tr>
            <td>Take profits</td>
            <td className={takeProfits ? undefined : 'none'}>
              {takeProfits || 'none'}
            </td>
          </tr>
          <tr>
            <td>Confidence</td>
            <td>{formatConfidence(signal.confidence)}</td>
          </tr>
          {detail.template && (
            <tr>
              <td>Template</td>
              <td>{detail.template}</td>
            </tr>
          )}
        </tbody>
      </table>
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

  const rowsByTab = useMemo(
    () => ({
      parsed: parsedRows(audit.parsedSignals, messageById, ruleById),
      ambiguous: ambiguousRows(audit.ambiguousCandidates, ruleByTemplateKey),
      rejected: rejectedRows(audit.rejectedCandidates),
      rare: rareRows(audit.rareTemplates),
      misses: missRows(audit.potentialMisses)
    }),
    [audit, messageById, ruleById, ruleByTemplateKey]
  )

  // Accepted families are named by FORMAT, so several can share one display name.
  // Tag each option with how many signals it parsed — a useful, distinguishing
  // discriminator so the dropdown options are not indistinguishable.
  const parsedCountByRule = useMemo(() => {
    const counts = new Map()
    for (const signal of audit.parsedSignals) {
      counts.set(signal.parserRuleId, (counts.get(signal.parserRuleId) || 0) + 1)
    }
    return counts
  }, [audit])

  const activeTab = TABS.find((entry) => entry.id === tab)
  const templateEnabled = activeTab.templated && rules.length > 0
  const effectiveTemplate = templateEnabled ? templateId : 'all'

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return rowsByTab[tab].filter(
      (row) =>
        (!needle || row.haystack.includes(needle)) &&
        (effectiveTemplate === 'all' || row.templateId === effectiveTemplate)
    )
  }, [rowsByTab, tab, query, effectiveTemplate])

  // Any filter change returns the list to the first page.
  useEffect(() => {
    setPage(0)
  }, [tab, query, effectiveTemplate])

  if (!hasAccepted) {
    return (
      <section className="vrs-tm-review">
        <div className="vrs-tm-section__head">
          <div>
            <div className="vrs-tm-section__title">Review results</div>
            <div className="vrs-tm-section__sub">
              Run the accepted rules over the full history
            </div>
          </div>
        </div>
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
    count: rowsByTab[entry.id].length
  }))

  return (
    <section className="vrs-tm-review">
      <div className="vrs-tm-section__head">
        <div>
          <div className="vrs-tm-section__title">Review results</div>
          <div className="vrs-tm-section__sub">
            Search and filter every message the parser sorted
          </div>
        </div>
      </div>

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
                  {row.template && (
                    <span className="vrs-tm-review__tmpl" title={row.template}>
                      {row.template}
                    </span>
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
