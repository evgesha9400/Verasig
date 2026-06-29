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
import { normalizeTemplate } from './template.js'

const INTENT_REASON = {
  update: 'Reads as an update to an open trade, not a new signal.',
  result: 'Reads as a trade result, not a new signal.',
  commentary: 'Reads as commentary, not a tradeable signal.'
}

function asMessage(message) {
  if (typeof message === 'string') return { id: `msg_${message.length}`, text: message }
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
 * @returns {import('./types.js').Candidate|null}
 */
export function attemptExtractSignal(input) {
  const message = asMessage(input)
  const { clean } = normalizeMessageText(message.text)
  const instruments = detectInstruments(clean)
  const directions = detectDirections(clean)
  if (instruments.length === 0 || directions.length === 0) return null

  const prices = detectPrices(clean)
  const fields = extractSignalFields(message)
  const intent = classifyIntent(message.text, fields)
  const geometry = validatePriceGeometry(fields)
  const confidence = scoreCandidate({ message, fields, directions })
  const { templateKey, normalizedTemplate } = normalizeTemplate({ message })
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
    templateKey,
    normalizedTemplate
  }
}
