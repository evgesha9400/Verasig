/* Verasig — Template Mining: intent classification.
   Parse-first means the parser is the classifier: a message is a new signal only
   when it parses into instrument + direction + some structure AND does not read
   as an outcome report (result), a position adjustment (update), or chatter
   (commentary). Markers are scored deterministically — no LLM. */

import { normalizeMessageText } from './text.js'

// Outcome reports: a trade that already played out. "profit" / "pips" only read
// as an outcome when quantified or verb-bound — bare "take profit" / "profit
// target" is forward-looking signal copy, not a result.
const RESULT_MARKERS = [
  /\bclosed\b/,
  /\bstopped(\s*out)?\b/,
  /\brunning\b/,
  /\b(tp\s*hit|sl\s*hit)\b/,
  /\b\d+(\.\d+)?\s*(pips?|points?|pts)\b/,
  /\b(banked|secured|booked|locked|took)\s+profits?\b/,
  /\bin\s+profit\b/,
  /\bsmashed\b/,
  /\bbanked\b/,
  /[+\-−]\d+(\.\d+)?\s*%/,
  // Russian outcome markers. Deliberately NOT "прибыл"/"фиксир" — those appear in
  // the new-signal boilerplate "Решение о фиксации прибыли".
  /результат/i,
  /заработано/i,
  /принесла/i
]
const HIT_NEAR_LEVEL = /\bhit\b/

// Strong management markers reference an existing position so unambiguously that
// they win even when the message restates entry/stop/target levels.
const STRONG_UPDATE_MARKERS = [
  /\bmove\b[^\n]{0,15}\b(sl|stop)\b/,
  /\bbreak\s*even\b/,
  /\bbreakeven\b/,
  /\bto\s*be\b/,
  /\bcancel(led)?\b/,
  /\bdelete\b/,
  /\baverag(e|ing)\b/,
  /\b(activated|triggered)\b/
]
// Soft markers ("close half", "partial", "hold the position", "secure profit")
// mean an update ONLY when the message is not itself a complete fresh setup — a
// scalp that posts entry+stop+target and then says "close half" is a new signal.
const SOFT_UPDATE_MARKERS = [
  /\bhold\s+(the\s+)?(trade|position|runner|runners|it|longs?|shorts?)\b/,
  /\bpartial(ly)?\b/,
  /\bclos(e|ing)\b/,
  /\bsecure(d)?\s+(profits?|gains?|partial|the\s+(bag|runner))\b/
]

const COMMENTARY_MARKERS = [
  /\blooks?\b/,
  /\bmaybe\b/,
  /\bmight\b/,
  /\bcould\b/,
  /\bshould\b/,
  /\bwait(ing)?\b/,
  /\bthinking\b/,
  /\banalysis\b/,
  /\bbias\b/,
  /\bexpect(ing)?\b/,
  /\bprobably\b/,
  /\bwatching\b/,
  /\bmay\b/
]

const LEVEL_NEARBY = /\b(tp\d*|sl|target)\b/

function anyMatch(markers, text) {
  return markers.some((marker) => marker.test(text))
}

function looksLikeResult(text) {
  if (anyMatch(RESULT_MARKERS, text)) return true
  return HIT_NEAR_LEVEL.test(text) && LEVEL_NEARBY.test(text)
}

function structureScore(fields) {
  let score = 0
  if (fields.entry) score += 1
  if (fields.stopLoss !== null && fields.stopLoss !== undefined) score += 1
  if (Array.isArray(fields.takeProfits) && fields.takeProfits.length > 0) score += 1
  return score
}

// A complete fresh trade: instrument + direction + an entry (or market order) +
// a stop + at least one target. Such a message is a new signal even if it ends
// with a soft management note like "close half".
function isCompleteSetup(fields, marketMarker) {
  return (
    Boolean(fields.instrument) &&
    Boolean(fields.direction) &&
    Boolean(fields.entry || marketMarker) &&
    fields.stopLoss !== null &&
    fields.stopLoss !== undefined &&
    Array.isArray(fields.takeProfits) &&
    fields.takeProfits.length > 0
  )
}

/**
 * @param {string} text
 * @param {Partial<import('./types.js').StructuredSignal>} fields
 * @returns {import('./types.js').SignalIntent}
 */
export function classifyIntent(text, fields = {}) {
  const { lower } = normalizeMessageText(text)
  const hasInstrument = Boolean(fields.instrument)
  const hasDirection = Boolean(fields.direction)
  const marketMarker = /\b(now|cmp|market)\b/.test(lower) || /по\s*рынк/i.test(lower)

  if (looksLikeResult(lower)) return 'result'
  if (anyMatch(STRONG_UPDATE_MARKERS, lower)) return 'update'
  if (isCompleteSetup(fields, marketMarker)) return 'new_signal'
  if (anyMatch(SOFT_UPDATE_MARKERS, lower)) return 'update'

  const structured = structureScore(fields) > 0 || marketMarker
  if (hasInstrument && hasDirection && structured) return 'new_signal'
  if (anyMatch(COMMENTARY_MARKERS, lower) || lower.includes('?')) return 'commentary'
  if (hasInstrument && hasDirection) return 'new_signal'
  return 'unknown'
}
