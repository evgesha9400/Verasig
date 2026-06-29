/* Verasig — Template Mining: confidence scoring.
   A transparent additive rubric: structural evidence adds, update/result markers
   subtract, geometry contributes its own adjustment. The raw score is normalized
   to 0..1. It is used for RANKING families and deciding review order — not as a
   precise probability — so thresholds matter more than exact values. */

import { normalizeMessageText } from './text.js'
import { detectDirections } from './directions.js'
import { validatePriceGeometry } from './geometry.js'

const NORMALIZER = 16 // a clean, fully-structured signal lands high (~0.9) but below saturation

const NEGATIVE_RULES = [
  { test: (t) => /\bhit\b/.test(t) && /\b(tp\d?|sl|target)\b/.test(t), penalty: -5 },
  { test: (t) => /\bclosed\b/.test(t), penalty: -5 },
  { test: (t) => /\bclos(e|ing)\b/.test(t), penalty: -4 },
  { test: (t) => /\bmove\s*(sl|stop)\b/.test(t), penalty: -4 },
  { test: (t) => /\b(breakeven|break\s*even|to\s*be)\b/.test(t), penalty: -4 },
  { test: (t) => /\bcancel(led)?\b/.test(t), penalty: -4 },
  { test: (t) => /\b(profits?|pips?|points?)\b/.test(t), penalty: -3 }
]

function candidateText(candidate) {
  return candidate.message?.text ?? candidate.text ?? ''
}

function candidateDirections(candidate, text) {
  return candidate.directions ?? detectDirections(text)
}

function isEmojiOnlyDirection(directions) {
  if (directions.length === 0) return false
  return directions.every((entity) => entity.confidence < 0.7)
}

function positiveScore(fields, lower, lineCount) {
  let score = 0
  if (fields.instrument) score += 3
  if (fields.direction) score += 3
  if (fields.entry) score += 2
  if (/\b(now|cmp|market)\b/.test(lower)) score += 1
  if (fields.stopLoss !== null && fields.stopLoss !== undefined) score += 2
  if (fields.takeProfits && fields.takeProfits.length > 0) score += 2
  const hasStructure =
    fields.entry || fields.stopLoss !== null || (fields.takeProfits?.length ?? 0) > 0
  if (lineCount <= 6 && fields.direction && hasStructure) score += 1
  return score
}

function negativeScore(fields, lower, directions) {
  let score = 0
  for (const rule of NEGATIVE_RULES) if (rule.test(lower)) score += rule.penalty
  const hasPrices =
    fields.entry || fields.stopLoss !== null || (fields.takeProfits?.length ?? 0) > 0
  const hasMarket = /\b(now|cmp|market)\b/.test(lower)
  if (!hasPrices && !hasMarket) score -= 1
  if (isEmojiOnlyDirection(directions)) score -= 1
  return score
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value))
}

/**
 * @param {import('./types.js').Candidate} candidate
 * @returns {number} confidence in [0, 1]
 */
export function scoreCandidate(candidate) {
  const text = candidateText(candidate)
  const fields = candidate.fields || {}
  const { lower, lines } = normalizeMessageText(text)
  const directions = candidateDirections(candidate, text)

  const raw =
    positiveScore(fields, lower, lines.length) +
    negativeScore(fields, lower, directions) +
    validatePriceGeometry(fields).scoreAdjustment

  return clamp01(raw / NORMALIZER)
}
