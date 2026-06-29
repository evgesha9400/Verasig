/* Verasig — Template Mining: template normalization.
   Turns a message into a structural skeleton by replacing the parts that vary
   (instruments, directions, prices, market markers) with placeholders, then
   uppercasing the label words the author actually wrote. Two messages with the
   same shape but different symbols and numbers collapse to one templateKey, so
   the user reviews format families instead of individual messages. */

import { normalizeMessageText } from './text.js'
import { detectInstruments } from './instruments.js'
import { detectDirections } from './directions.js'
import { detectPrices } from './prices.js'

const MARKET_MARKER = /\b(current market price|current price|cmp|market|now)\b/gi
const LIST_GAP = /^[\s/,]*$/

function instrumentSpans(clean) {
  return detectInstruments(clean).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: '<INSTRUMENT>'
  }))
}

function directionSpans(clean) {
  return detectDirections(clean).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: entity.confidence < 0.7 ? '<SIDE_EMOJI>' : '<SIDE>'
  }))
}

// Consecutive single levels separated only by list punctuation become one
// <PRICE_LIST>; a range is always its own <RANGE>; a lone level is a <PRICE>.
function priceSpans(clean) {
  const prices = detectPrices(clean)
  const spans = []
  let group = []
  const flush = () => {
    if (group.length === 0) return
    const token = group.length >= 2 ? '<PRICE_LIST>' : '<PRICE>'
    spans.push({ start: group[0].start, end: group[group.length - 1].end, token })
    group = []
  }
  for (const price of prices) {
    if (price.type === 'range') {
      flush()
      spans.push({ start: price.start, end: price.end, token: '<RANGE>' })
      continue
    }
    const previous = group[group.length - 1]
    const joinable = previous && LIST_GAP.test(clean.slice(previous.end, price.start))
    if (previous && !joinable) flush()
    group.push(price)
  }
  flush()
  return spans
}

function marketSpans(clean) {
  const spans = []
  let match
  MARKET_MARKER.lastIndex = 0
  while ((match = MARKET_MARKER.exec(clean)) !== null) {
    spans.push({
      start: match.index,
      end: match.index + match[0].length,
      token: 'MARKET'
    })
  }
  return spans
}

function collectSpans(clean) {
  const spans = [
    ...instrumentSpans(clean),
    ...directionSpans(clean),
    ...priceSpans(clean),
    ...marketSpans(clean)
  ].sort((a, b) => a.start - b.start || b.end - a.end)

  const accepted = []
  let cursor = -1
  for (const span of spans) {
    if (span.start < cursor) continue // drop overlap
    accepted.push(span)
    cursor = span.end
  }
  return accepted
}

function applySpans(clean, spans) {
  let result = ''
  let cursor = 0
  for (const span of spans) {
    result += clean.slice(cursor, span.start) + span.token
    cursor = span.end
  }
  return result + clean.slice(cursor)
}

function tidyLines(text) {
  return text
    .split('\n')
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter((line) => line.length > 0)
    .join('\n')
}

// A numbered TP that owns a value keeps its ordinal ("TP1: <PRICE>"); a bare
// reference collapses to TP<N> so "hit TP1"/"hit TP2" updates group together. A
// function replacer matches the whole ordinal (avoiding the digit-backtracking
// that corrupted "TP10" into "TP<N>0").
function collapseBareOrdinals(template) {
  return template.replace(/\bTP\d+\b/g, (match, offset, full) => {
    const after = full.slice(offset + match.length)
    return /^:?\s*<PRICE/.test(after) ? match : 'TP<N>'
  })
}

export function hashString(text) {
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0
  }
  return hash.toString(36)
}

/**
 * @param {import('./types.js').Candidate|{message?: {text?: string}, text?: string}} candidate
 * @returns {{templateKey: string, normalizedTemplate: string}}
 */
export function normalizeTemplate(candidate) {
  const text = candidate.message?.text ?? candidate.text ?? ''
  const { clean } = normalizeMessageText(text)
  const spans = collectSpans(clean)
  const replaced = applySpans(clean, spans).toUpperCase()
  const normalizedTemplate = collapseBareOrdinals(tidyLines(replaced))
  return { templateKey: `tpl_${hashString(normalizedTemplate)}`, normalizedTemplate }
}
