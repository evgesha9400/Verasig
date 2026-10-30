/* Verasig — Template Mining: presentation helpers.
   Pure formatting for the prototype UI — no business logic lives here. */

export const INTENT_ORDER = ['new_signal', 'update', 'result', 'commentary', 'unknown']

export const INTENT_LABEL = {
  new_signal: 'New signal',
  update: 'Update',
  result: 'Result',
  commentary: 'Commentary',
  unknown: 'Unknown'
}

export const ACTION_TONE = { accept: 'verified', review: 'pending', reject: 'rejected' }
export const ACTION_LABEL = {
  accept: 'Suggest accept',
  review: 'Needs review',
  reject: 'Suggest reject'
}

export function formatPrice(value) {
  if (!Number.isFinite(value)) return '—'
  if (Number.isInteger(value) && Math.abs(value) >= 1000) {
    return value.toLocaleString('en-US')
  }
  return String(value)
}

export function formatEntry(entry) {
  if (!entry) return 'Market'
  if (entry.type === 'range')
    return `${formatPrice(entry.min)}–${formatPrice(entry.max)}`
  if (typeof entry.price === 'number') return formatPrice(entry.price)
  return '—'
}

export function formatTakeProfits(takeProfits) {
  if (!takeProfits || takeProfits.length === 0) return null
  return takeProfits.map(formatPrice).join(', ')
}

export function formatPercent(ratio) {
  if (!Number.isFinite(ratio)) return '0%'
  return `${Math.round(ratio * 100)}%`
}

export function formatConfidence(value) {
  if (!Number.isFinite(value)) return '—'
  return `${Math.round(value * 100)}%`
}

// A message timestamp for display. An ISO string (posted_at.isoformat()) becomes a
// compact locale label; a demo/prototype string ("Jun 6 08:42") passes through
// untouched; empty is ''. Never throws — an unparseable value is returned as-is.
export function formatMessageDate(date) {
  if (!date) return ''
  const text = String(date)
  if (!/^\d{4}-\d{2}-\d{2}[T ]/.test(text)) return text
  const parsed = new Date(text)
  if (Number.isNaN(parsed.getTime())) return text
  return parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

// The audit review ranks rows within a page by whichever accepted family
// covers more messages, ties broken by confidence.
export function byCoverageThenConfidence(coverageOf, confidenceOf) {
  return (a, b) => coverageOf(b) - coverageOf(a) || confidenceOf(b) - confidenceOf(a)
}

// Comparator: newest message first. Two parseable dates → later timestamp leads; a
// dated item leads an undated one; two undated items hold their input order (stable,
// so a coverage/confidence tiebreak downstream still decides dateless rows).
export function byMessageDateDesc(dateOf) {
  const timeOf = (item) => {
    const value = dateOf(item)
    if (!value) return null
    const time = Date.parse(value)
    return Number.isNaN(time) ? null : time
  }
  return (a, b) => {
    const ta = timeOf(a)
    const tb = timeOf(b)
    if (ta === null && tb === null) return 0
    if (ta === null) return 1
    if (tb === null) return -1
    return tb - ta
  }
}
