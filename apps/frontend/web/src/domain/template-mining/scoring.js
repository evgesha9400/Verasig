/* Verasig — Template Mining: confidence scoring.
   A transparent additive rubric: structural evidence adds, update/result markers
   subtract, geometry contributes its own adjustment. The raw score is normalized
   to 0..1. It is used for RANKING families and deciding review order — not as a
   precise probability — so thresholds matter more than exact values. */

import { normalizeMessageText } from './text.js'
import { detectDirections, isEmojiOnlyDirection } from './directions.js'
import { validatePriceGeometry } from './geometry.js'
import { hasStopLoss, hasTakeProfits } from './intent.js'

const NORMALIZER = 16 // a clean, fully-structured signal lands high (~0.9) but below saturation

const NEGATIVE_RULES = [
  { test: (t) => /\bhit\b/.test(t) && /\b(tp\d*|sl|target)\b/.test(t), penalty: -5 },
  { test: (t) => /\bclosed\b/.test(t), penalty: -5 },
  { test: (t) => /\bclos(e|ing)\b/.test(t), penalty: -4 },
  { test: (t) => /\bmove\s*(sl|stop)\b/.test(t), penalty: -4 },
  { test: (t) => /\b(breakeven|break\s*even|to\s*be)\b/.test(t), penalty: -4 },
  { test: (t) => /\bcancel(led)?\b/.test(t), penalty: -4 },
  // Quantified P&L or "in profit" reads as an outcome; bare "take profit" does not.
  {
    test: (t) =>
      /\b\d+(\.\d+)?\s*(pips?|points?|pts)\b/.test(t) || /\bin\s+profit\b/.test(t),
    penalty: -3
  }
]

/** @param {import('./types.js').Candidate|{message?: {text?: string}, text?: string}} candidate */
export function candidateText(candidate) {
  return candidate.message?.text ?? candidate.text ?? ''
}

function candidateDirections(candidate, text) {
  return candidate.directions ?? detectDirections(text)
}

function hasStructuredPrices(fields) {
  return Boolean(
    fields.entry || fields.stopLoss !== null || (fields.takeProfits?.length ?? 0) > 0
  )
}

function positiveScore(fields, lower, lineCount) {
  let score = 0
  if (fields.instrument) score += 3
  if (fields.direction) score += 3
  if (fields.entry) score += 2
  if (/\b(now|cmp|market)\b/.test(lower)) score += 1
  if (hasStopLoss(fields)) score += 2
  if (hasTakeProfits(fields)) score += 2
  if (lineCount <= 6 && fields.direction && hasStructuredPrices(fields)) score += 1
  return score
}

function negativeScore(fields, lower, directions) {
  let score = 0
  for (const rule of NEGATIVE_RULES) if (rule.test(lower)) score += rule.penalty
  const hasMarket = /\b(now|cmp|market)\b/.test(lower)
  if (!hasStructuredPrices(fields) && !hasMarket) score -= 1
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
  const geometry = candidate.geometry ?? validatePriceGeometry(fields)

  const raw =
    positiveScore(fields, lower, lines.length) +
    negativeScore(fields, lower, directions) +
    geometry.scoreAdjustment

  return clamp01(raw / NORMALIZER)
}
