/* Verasig — Template Mining: price detection.
   Pulls numeric levels and min/max ranges out of a message while stepping around
   the things that look numeric but are not prices: numbered TP labels ("TP1"),
   clock times ("08:42") and leverage ("5-10x"). Ranges are scanned first and
   their spans reserved so the two levels of a range are never re-read as singles. */

const NUMBER = '(?:\\d{1,3}(?:,\\d{3})+|\\d+)(?:\\.\\d+)?[kKmM]?'
// Clock times, optionally with seconds, so "08:42:15" is reserved whole and its
// ":15" tail is not read as a price.
const TIME = /\b\d{1,2}:\d{2}(?::\d{2})?\b/g
// A numbered target ordinal written apart from its value ("TP 1 2340", "TP 1: 2340").
// The ordinal is a short integer followed by another number — reserve it so it is
// not read as a take-profit level. A bare "TP 50" (value, no following number) is left alone.
const TARGET_ORDINAL = /\b(?:tp|tgt|targets?)\s+\d{1,2}\b(?=[\s:]*\d)/gi
// Keycap-emoji ordinals (1️⃣ 2️⃣ …) prefix numbered target lines; the digit is a
// label, not a price. Matches digit + optional VS16 + the keycap combiner.
const KEYCAP = /[0-9]\uFE0F?\u20E3/g
const SINGLE = new RegExp(`(?<![A-Za-z\\d.,])(${NUMBER})`, 'g')
const RANGE = new RegExp(
  `(?<![A-Za-z\\d.,])(${NUMBER})\\s*(?:-|to)\\s*(${NUMBER})`,
  'gi'
)

/**
 * @param {string} raw
 * @returns {number}
 */
export function parseNumber(raw) {
  const text = String(raw).replace(/,/g, '').trim()
  const suffix = text.slice(-1).toLowerCase()
  const scale = suffix === 'k' ? 1000 : suffix === 'm' ? 1000000 : 1
  const numeric = scale === 1 ? text : text.slice(0, -1)
  return parseFloat(numeric) * scale
}

// Leverage ("10x") and percentages ("2%") only count when glued to the number;
// a space means the next token is an ordinary word, not a unit. P&L units
// ("+300 pips") are matched as whole words and so tolerate the space.
const TRAILING_UNIT_WORD = /^\s*(pips?|points?|pts|pct|percent)\b/i

function hasUnitSuffix(text, endIndex) {
  // x / Latin X / Cyrillic kha (leverage "20X"/"20kha") and % are never price levels.
  if (/[xX\u0445\u0425%]/.test(text[endIndex] || '')) return true
  return TRAILING_UNIT_WORD.test(text.slice(endIndex))
}

function spansOf(regex, text, spans) {
  let match
  regex.lastIndex = 0
  while ((match = regex.exec(text)) !== null) {
    spans.push([match.index, match.index + match[0].length])
  }
}

function blockedSpans(text) {
  const spans = []
  spansOf(TIME, text, spans)
  spansOf(TARGET_ORDINAL, text, spans)
  spansOf(KEYCAP, text, spans)
  return spans
}

function within(index, spans) {
  return spans.some(([start, end]) => index >= start && index < end)
}

function overlaps(start, end, spans) {
  return spans.some(([spanStart, spanEnd]) => start < spanEnd && spanStart < end)
}

function collectRanges(text, blocked, reserved, prices) {
  let match
  RANGE.lastIndex = 0
  while ((match = RANGE.exec(text)) !== null) {
    const end = match.index + match[0].length
    // Reserve the span unconditionally so a rejected range (leverage like
    // "5-10x") still suppresses its two numbers from the single-level scan.
    reserved.push([match.index, end])
    if (overlaps(match.index, end, blocked) || hasUnitSuffix(text, end)) continue
    const a = parseNumber(match[1])
    const b = parseNumber(match[2])
    prices.push({
      raw: match[0],
      min: Math.min(a, b),
      max: Math.max(a, b),
      type: 'range',
      start: match.index,
      end
    })
  }
}

function collectSingles(text, blocked, reserved, prices) {
  let match
  SINGLE.lastIndex = 0
  while ((match = SINGLE.exec(text)) !== null) {
    const end = match.index + match[0].length
    if (within(match.index, blocked) || within(match.index, reserved)) continue
    if (hasUnitSuffix(text, end)) continue
    prices.push({
      raw: match[0],
      value: parseNumber(match[1]),
      type: 'single',
      start: match.index,
      end
    })
  }
}

/**
 * @param {string} text
 * @returns {import('./types.js').DetectedPrice[]}
 */
export function detectPrices(text) {
  if (!text) return []
  const blocked = blockedSpans(text)
  const reserved = []
  const prices = []
  collectRanges(text, blocked, reserved, prices)
  collectSingles(text, blocked, reserved, prices)
  return prices.sort((a, b) => a.start - b.start)
}
