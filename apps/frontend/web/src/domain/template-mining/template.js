/* Verasig — Template Mining: template normalization.
   Turns a message into a structural skeleton by replacing the parts that vary
   (instruments, directions, prices, market markers) with placeholders, then
   uppercasing the label words the author actually wrote. Two messages with the
   same shape but different symbols and numbers collapse to one templateKey, so
   the user reviews format families instead of individual messages. */

import { normalizeMessageText, toCleanLines } from './text.js'
import { detectInstruments } from './instruments.js'
import { detectDirections, isEmojiDirection } from './directions.js'
import { detectPrices } from './prices.js'

const MARKET_MARKER = /\b(current market price|current price|cmp|market|now)\b/gi
const LIST_GAP = /^[\s/,]*$/

function instrumentSpans(clean, overlay) {
  return detectInstruments(clean, overlay).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: '<INSTRUMENT>'
  }))
}

function directionSpans(clean, overlay) {
  return detectDirections(clean, overlay).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: isEmojiDirection(entity) ? '<SIDE_EMOJI>' : '<SIDE>'
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

function collectSpans(clean, overlay) {
  const spans = [
    ...instrumentSpans(clean, overlay),
    ...directionSpans(clean, overlay),
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
  return toCleanLines(text).join('\n')
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

// Leverage tokens ("20X", "17X", Cyrillic "20Х") vary per signal but are not
// structural — collapse them so a format isn't split into one family per leverage.
const LEVERAGE_TOKEN = /\d+\s*[X\u0425](?![A-Za-z\u0400-\u04FF0-9])/g
function collapseLeverage(template) {
  return template.replace(LEVERAGE_TOKEN, '<LEVERAGE>')
}

// Decoration that varies per message and must not split a format family:
// non-direction emojis, currency symbols, colons, bullets, hashes, punctuation.
// Keep only letters, digits, whitespace and placeholder characters (< > _ @).
const DECORATIVE_EMOJI = /[\p{Extended_Pictographic}\uFE0F\u20E3\u200D]/gu
const NON_STRUCTURAL = /[^\p{L}\p{N}\s<>_@\n]/gu
const SIDE_EMOJI_RUN = /(?:<SIDE_EMOJI>\s*)+/g
const PRICE_RUN = /<PRICE>(?:\s+<PRICE>)+/g

// The structural vocabulary: the label words that actually shape a signal. Any
// other word is incidental channel chatter and is wildcarded to <*>. Kept as
// data so new label dialects extend it without touching the matcher.
const STRUCT_WORDS = new Set([
  // English
  'BUY',
  'SELL',
  'LONG',
  'SHORT',
  'CALL',
  'PUT',
  'ENTRY',
  'ENTER',
  'ENTRIES',
  'ZONE',
  'LIMIT',
  'ORDER',
  'MARKET',
  'NOW',
  'CMP',
  'CURRENT',
  'PRICE',
  'STOP',
  'STOPLOSS',
  'SL',
  'INVALIDATION',
  'INVALID',
  'BELOW',
  'ABOVE',
  'TP',
  'TAKE',
  'PROFIT',
  'PROFITS',
  'TARGET',
  'TARGETS',
  'TGT',
  'PARTIAL',
  'HIT',
  'RANGE',
  'LEVERAGE',
  // Russian
  'МОНЕТА',
  'МОНЕТУ',
  'МОНЕТЕ',
  'ПОКУПКА',
  'ПРОДАЖА',
  'КУПИЛ',
  'ПРОДАЛ',
  'ЛОНГ',
  'ШОРТ',
  'ПЛЕЧО',
  'ВХОД',
  'СТОП',
  'ЦЕЛИ',
  'ЦЕЛЬ',
  'ЦЕЛЕЙ',
  'ТЕЙК',
  'ТЕЙКИ',
  'ФИКСИРУЕМ',
  'ПРИБЫЛЬ',
  'ПРИБЫЛИ',
  'НА',
  'ПО',
  'РЫНКУ',
  'В'
])
// A line must carry at least one of these value placeholders to be a field line.
const VALUE_PLACEHOLDER =
  /<(?:INSTRUMENT|PRICE|PRICE_LIST|RANGE|SIDE|SIDE_EMOJI|LEVERAGE|N)>/
const TOKEN = /<[A-Z_]+>|[\p{L}][\p{L}\p{N}]*/gu

function stripDecoration(template) {
  return template.replace(DECORATIVE_EMOJI, '').replace(NON_STRUCTURAL, ' ')
}

// "<PRICE> <PRICE> <PRICE>" (a target list, whatever punctuation once joined it)
// collapses to one <PRICE_LIST>, per line so separate fields never merge.
function collapsePriceRuns(template) {
  return template
    .split('\n')
    .map((line) => line.replace(PRICE_RUN, '<PRICE_LIST>'))
    .join('\n')
}

// Consecutive bare price lines (a target list written one-per-line, e.g.
// "1 <PRICE>" / "2 <PRICE>" / "3 <PRICE>") collapse to one <PRICE_LIST> so the
// same format doesn't split by how many targets it happened to list.
const BARE_PRICE_LINE = /^(?:\d+\s+)?<PRICE>$/
function collapseTargetLines(template) {
  const out = []
  let run = 0
  const flush = () => {
    if (run > 0) out.push(run >= 2 ? '<PRICE_LIST>' : '<PRICE>')
    run = 0
  }
  for (const line of template.split('\n')) {
    if (BARE_PRICE_LINE.test(line)) {
      run += 1
      continue
    }
    flush()
    out.push(line)
  }
  flush()
  return out.join('\n')
}

const PRICE_OR_RANGE = /<(?:PRICE|RANGE)>/
const TARGET_LIST_LABEL = /\b(?:TAKE PROFITS|TARGETS|PARTIAL)\b/
const TARGET_LIST_LABEL_RU = [
  'ЦЕЛИ',
  'ЦЕЛЬ',
  'ЦЕЛЕЙ',
  'ТЕЙК',
  'ТЕЙКИ',
  'ФИКСИРУЕМ ПРИБЫЛЬ НА'
]
const INDEPENDENT_ENTRY_LABEL = /\b(?:ENTRY|ENTRIES|ENTER|ZONE)\b|@/

function lineHasTargetListLabel(line) {
  return (
    TARGET_LIST_LABEL.test(line) ||
    TARGET_LIST_LABEL_RU.some((label) => line.includes(label))
  )
}

function lineHasIndependentPricedEntry(line) {
  if (!PRICE_OR_RANGE.test(line)) return false
  return INDEPENDENT_ENTRY_LABEL.test(line) || line.includes('ВХОД')
}

function canonicalizeTargetPriceArity(line) {
  if (!lineHasTargetListLabel(line)) return line
  return line.replace(/<PRICE>$/, '<PRICE_LIST>')
}

function canonicalizeLimitOrderModifier(line, hasIndependentPricedEntry) {
  if (!hasIndependentPricedEntry || PRICE_OR_RANGE.test(line)) return line
  return line
    .replace(/(^|\s)LIMIT ORDER\b/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()
}

function canonicalizeTemplateFamily(template) {
  const lines = template.split('\n')
  const hasIndependentPricedEntry = lines.some(lineHasIndependentPricedEntry)
  return lines
    .map((line) => canonicalizeLimitOrderModifier(line, hasIndependentPricedEntry))
    .map(canonicalizeTargetPriceArity)
    .join('\n')
}

// Wildcard non-structural words to <*>, counting how many a line contains. A
// real field line is known labels + placeholders with at most ONE stray word (a
// label synonym), which becomes <*>; lines with more stray words are channel
// chatter (promos, news, analysis) and are dropped — so a pure-chatter message
// reduces to nothing and is not a signal candidate at all.
const MAX_STRAY_WORDS = 1
function wildcardLine(line) {
  let stray = 0
  const mapped = line.replace(TOKEN, (token) => {
    if (token.startsWith('<')) return token
    const upper = token.toUpperCase()
    if (STRUCT_WORDS.has(upper) || /^TP\d*$/.test(upper)) return upper
    stray += 1
    return '<*>'
  })
  const compact = mapped
    .replace(/(?:<\*>\s*)+/g, '<*> ')
    .replace(/\s+/g, ' ')
    .trim()
  return { line: compact, stray }
}

function keepStructuralLines(template) {
  return template
    .split('\n')
    .map(wildcardLine)
    .filter(
      ({ line, stray }) => stray <= MAX_STRAY_WORDS && VALUE_PLACEHOLDER.test(line)
    )
    .map(({ line }) => line)
    .join('\n')
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
 * @param {object} [overlay={}]
 * @returns {{templateKey: string, normalizedTemplate: string}}
 */
export function normalizeTemplate(candidate, overlay = {}) {
  const text = candidate.message?.text ?? candidate.text ?? ''
  const { clean } = normalizeMessageText(text)
  const spans = collectSpans(clean, overlay)
  const replaced = stripDecoration(applySpans(clean, spans).toUpperCase()).replace(
    SIDE_EMOJI_RUN,
    '<SIDE_EMOJI> '
  )
  let skeleton = collapsePriceRuns(tidyLines(replaced))
  skeleton = collapseLeverage(collapseBareOrdinals(skeleton))
  skeleton = keepStructuralLines(collapseTargetLines(skeleton))
  skeleton = canonicalizeTemplateFamily(skeleton)
  return { templateKey: `tpl_${hashString(skeleton)}`, normalizedTemplate: skeleton }
}
