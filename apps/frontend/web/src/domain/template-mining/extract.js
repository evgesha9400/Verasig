/* Verasig — Template Mining: candidate extraction.
   Assembles the detectors, extractor, intent classifier, scorer, geometry check
   and template normalizer into one Candidate. The minimum bar is instrument +
   direction; below it the message is not a signal candidate and we return null —
   the parser itself is the classifier. */

import { normalizeMessageText } from './text.js'
import { detectInstruments } from './instruments.js'
import { detectDirections } from './directions.js'
import { detectPrices } from './prices.js'
import { extractSignalFields } from './fields.js'
import { classifyIntent } from './intent.js'
import { scoreCandidate } from './scoring.js'
import { validatePriceGeometry } from './geometry.js'
import { normalizeTemplate, hashString } from './template.js'

const INTENT_REASON = {
  update: 'Reads as an update to an open trade, not a new signal.',
  result: 'Reads as a trade result, not a new signal.',
  commentary: 'Reads as commentary, not a tradeable signal.'
}

function asMessage(message) {
  // Hash the content so two distinct same-length strings get distinct ids
  // (length-based ids collided and corrupted sourceMessageIds provenance).
  if (typeof message === 'string')
    return { id: `msg_${hashString(message)}`, text: message }
  return message
}

function isEmojiOnlyDirection(directions) {
  return directions.length > 0 && directions.every((entity) => entity.confidence < 0.7)
}

function collectRejectionReasons(intent, fields, directions, geometry) {
  const reasons = [...geometry.warnings]
  if (INTENT_REASON[intent]) reasons.push(INTENT_REASON[intent])
  if (isEmojiOnlyDirection(directions)) {
    reasons.push('Direction is inferred from an emoji only.')
  }
  return reasons
}

/**
 * @param {import('./types.js').ChatMessage|string} input
 * @param {object} [overlay={}]
 * @returns {import('./types.js').Candidate|null}
 */
export function attemptExtractSignal(input, overlay = {}) {
  const message = asMessage(input)
  const { clean } = normalizeMessageText(message.text)
  const instruments = detectInstruments(clean, overlay)
  const directions = detectDirections(clean, overlay)
  if (instruments.length === 0 || directions.length === 0) return null

  const fields = extractSignalFields(message, overlay)
  const intent = classifyIntent(message.text, fields)
  // The parser is the classifier: only a message that reads as a NEW signal is a
  // candidate / template family. Updates, results and commentary are not new
  // signals — they are surfaced in the audit re-scan, not as signal formats.
  if (intent !== 'new_signal') return null

  const { templateKey, normalizedTemplate } = normalizeTemplate({ message }, overlay)
  // No structural skeleton survived (the message was directional prose, not a
  // formatted signal) — it is not a parseable signal format.
  if (!normalizedTemplate.trim()) return null

  const prices = detectPrices(clean)
  const geometry = validatePriceGeometry(fields)
  const confidence = scoreCandidate({ message, fields, directions })
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

/**
 * Intent of any message (instrument/direction not required) — used by the audit
 * re-scan to bucket non-candidate messages (updates/results) without making them
 * template families.
 * @param {import('./types.js').ChatMessage|string} input
 * @param {object} [overlay={}]
 * @returns {import('./types.js').SignalIntent}
 */
export function classifyMessageIntent(input, overlay = {}) {
  const message = asMessage(input)
  return classifyIntent(message.text, extractSignalFields(message, overlay))
}
