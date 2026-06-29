/* Verasig — Template Mining: price detection.
   Pulls numeric levels and min/max ranges out of a message while stepping around
   the things that look numeric but are not prices: numbered TP labels ("TP1"),
   clock times ("08:42") and leverage ("5-10x"). Ranges are scanned first and
   their spans reserved so the two levels of a range are never re-read as singles. */

const NUMBER = '(?:\\d{1,3}(?:,\\d{3})+|\\d+)(?:\\.\\d+)?[kKmM]?'
const TIME = /\b\d{1,2}:\d{2}\b/g
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

function trailingChar(text, index) {
  const rest = text.slice(index).match(/^\s*(\S)/)
  return rest ? rest[1] : ''
}

// Leverage ("10x") and percentages ("2%") read as numbers but are never price
// levels, so a number with one of these unit suffixes is dropped.
function hasUnitSuffix(text, endIndex) {
  return /[xX%]/.test(trailingChar(text, endIndex))
}

function blockedSpans(text) {
  const spans = []
  let match
  TIME.lastIndex = 0
  while ((match = TIME.exec(text)) !== null) {
    spans.push([match.index, match.index + match[0].length])
  }
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
