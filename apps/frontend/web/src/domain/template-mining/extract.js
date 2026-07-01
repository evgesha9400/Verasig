/* Verasig — Template Mining: candidate extraction.
   Assembles the detectors, extractor, intent classifier, scorer, geometry check
   and template normalizer into one Candidate. The minimum bar is instrument +
   direction; below it the message is not a signal candidate and we return null —
   the parser itself is the classifier. */

import { normalizeMessageText } from './text.js'
import { detectInstruments } from './instruments.js'
import { detectDirections, isEmojiOnlyDirection } from './directions.js'
import { detectPrices } from './prices.js'
import { extractSignalFields } from './fields.js'
import { classifyIntent } from './intent.js'
import { scoreCandidate } from './scoring.js'
import { validatePriceGeometry } from './geometry.js'
import { normalizeTemplate, hashString } from './template.js'
import { weakMemo } from './weakMemo.js'

function asMessage(message) {
  // Hash the content so two distinct same-length strings get distinct ids
  // (length-based ids collided and corrupted sourceMessageIds provenance).
  if (typeof message === 'string')
    return { id: `msg_${hashString(message)}`, text: message }
  return message
}

function intentRejectionReason(intent) {
  if (intent === 'update')
    return 'Reads as an update to an open trade, not a new signal.'
  if (intent === 'result') return 'Reads as a trade result, not a new signal.'
  if (intent === 'commentary') return 'Reads as commentary, not a tradeable signal.'
  return null
}

function collectRejectionReasons(intent, fields, directions, geometry) {
  const reasons = [...geometry.warnings]
  const intentReason = intentRejectionReason(intent)
  if (intentReason) reasons.push(intentReason)
  if (isEmojiOnlyDirection(directions)) {
    reasons.push('Direction is inferred from an emoji only.')
  }
  return reasons
}

// Mining (family discovery) and auditing (routing the full history against
// accepted rules) both extract every message — and re-run on every accept/
// reject decision. A message's detectors/fields/intent depend only on its own
// text and the overlay, so cache the analysis per (message, overlay) pair
// rather than recomputing it on every pass over the same history — including
// the audit's non-candidate routing, which needs the same intent and detector
// output a rejected candidate already computed and discarded.
const analysisCache = new WeakMap()
const candidateCache = new WeakMap()

function isCacheableMessage(message) {
  return typeof message === 'object' && message !== null
}

function cached(cache, message, overlay, compute) {
  if (!isCacheableMessage(message)) return compute(message, overlay)
  const cacheForMessage = weakMemo(cache, message, () => new WeakMap())
  if (cacheForMessage.has(overlay)) return cacheForMessage.get(overlay)
  const value = compute(message, overlay)
  cacheForMessage.set(overlay, value)
  return value
}

function computeAnalysis(message, overlay) {
  const normalized = normalizeMessageText(message.text)
  const { clean, lower, lines } = normalized
  const instruments = detectInstruments(clean, overlay)
  const directions = detectDirections(clean, overlay)
  const fields = extractSignalFields(message, overlay, {
    instruments,
    directions,
    normalized
  })
  const intent = classifyIntent(message.text, fields)
  return { clean, lower, lines, instruments, directions, fields, intent }
}

/**
 * Detectors, extracted fields and intent for any message — the shared analysis
 * every downstream step (candidacy, non-candidate routing, potential-miss
 * detection) is built from.
 * @param {import('./types.js').ChatMessage} message
 * @param {object} [overlay={}]
 * @returns {{clean: string, lower: string, lines: string[], instruments: import('./types.js').DetectedEntity[], directions: import('./types.js').DetectedEntity[], fields: object, intent: import('./types.js').SignalIntent}}
 */
export function analyzeMessage(message, overlay = {}) {
  return cached(analysisCache, message, overlay, computeAnalysis)
}

/**
 * @param {import('./types.js').ChatMessage|string} input
 * @param {object} [overlay={}]
 * @returns {import('./types.js').Candidate|null}
 */
export function attemptExtractSignal(input, overlay = {}) {
  const message = asMessage(input)
  return cached(candidateCache, message, overlay, computeCandidate)
}

function computeCandidate(message, overlay) {
  const { clean, lower, lines, instruments, directions, fields, intent } = analyzeMessage(
    message,
    overlay
  )
  if (instruments.length === 0 || directions.length === 0) return null
  // The parser is the classifier: only a message that reads as a NEW signal is a
  // candidate / template family. Updates, results and commentary are not new
  // signals — they are surfaced in the audit re-scan, not as signal formats.
  if (intent !== 'new_signal') return null

  const prices = detectPrices(clean)
  const { templateKey, normalizedTemplate } = normalizeTemplate({ message }, overlay, {
    instruments,
    directions,
    prices
  })
  // No structural skeleton survived (the message was directional prose, not a
  // formatted signal) — it is not a parseable signal format.
  if (!normalizedTemplate.trim()) return null

  const geometry = validatePriceGeometry(fields)
  const confidence = scoreCandidate({ message, fields, directions, geometry, lower, lines })
  const rejectionReasons = collectRejectionReasons(intent, fields, directions, geometry)

  return {
    message,
    instruments,
    directions,
    prices,
    fields,
    intent,
    confidence,
    rejectionReasons,
    parserIssues: geometry.issues,
    templateKey,
    normalizedTemplate
  }
}
