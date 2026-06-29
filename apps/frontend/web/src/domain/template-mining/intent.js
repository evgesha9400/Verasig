/* Verasig — Template Mining: intent classification.
   Parse-first means the parser is the classifier: a message is a new signal only
   when it parses into instrument + direction + some structure AND does not read
   as an outcome report (result), a position adjustment (update), or chatter
   (commentary). Markers are scored deterministically — no LLM. */

import { normalizeMessageText } from './text.js'

// Outcome reports: a trade that already played out.
const RESULT_MARKERS = [
  /\bclosed\b/,
  /\bstopped(\s*out)?\b/,
  /\brunning\b/,
  /\b(tp\s*hit|sl\s*hit)\b/,
  /\b\d+(\.\d+)?\s*(pips?|points?|pts)\b/,
  /\bpips?\b/,
  /\bprofits?\b/,
  /\bsmashed\b/,
  /\bbanked\b/,
  /[+\-−]\d+(\.\d+)?\s*%/
]
const HIT_NEAR_LEVEL = /\bhit\b/

// Position management: an instruction against an open trade.
const UPDATE_MARKERS = [
  /\bmove\s*(sl|stop)\b/,
  /\bbreak\s*even\b/,
  /\bbreakeven\b/,
  /\bto\s*be\b/,
  /\bcancel(led)?\b/,
  /\bdelete\b/,
  /\bhold\b/,
  /\baverag(e|ing)\b/,
  /\bpartial(ly)?\b/,
  /\b(activated|triggered)\b/,
  /\bclos(e|ing)\b/,
  /\bsecure(d)?\b/
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

const LEVEL_NEARBY = /\b(tp\d?|sl|target)\b/

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

/**
 * @param {string} text
 * @param {Partial<import('./types.js').StructuredSignal>} fields
 * @returns {import('./types.js').SignalIntent}
 */
export function classifyIntent(text, fields = {}) {
  const { lower } = normalizeMessageText(text)
  const hasInstrument = Boolean(fields.instrument)
  const hasDirection = Boolean(fields.direction)
  const marketMarker = /\b(now|cmp|market)\b/.test(lower)

  if (looksLikeResult(lower)) return 'result'
  if (anyMatch(UPDATE_MARKERS, lower)) return 'update'

  const structured = structureScore(fields) > 0 || marketMarker
  if (hasInstrument && hasDirection && structured) return 'new_signal'
  if (anyMatch(COMMENTARY_MARKERS, lower) || lower.includes('?')) return 'commentary'
  if (hasInstrument && hasDirection) return 'new_signal'
  return 'unknown'
}
