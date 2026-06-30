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
