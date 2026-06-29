/* Verasig — Template Mining: structured field extraction.
   Signals are line-structured, so each line is classified by the label it carries
   (stop / target / entry / market) and its prices are routed to that field. A
   header line that names the instrument or direction and carries a bare price is
   read as the entry only when no labelled entry line claims it. */

import { detectDirections } from './directions.js'
import { detectInstruments } from './instruments.js'
import { detectPrices } from './prices.js'
import { normalizeMessageText } from './text.js'

// "risk" is intentionally excluded: "Risk 2% / Risk 50 Reward 150" is position-
// sizing metadata, not a stop level, so it must not capture a stop value.
const STOP_LABEL = /\b(sl|stop\s*loss|stoploss|stop|invalidation|invalid\b)\b/i
const TARGET_LABEL = /\b(tp\d*|take\s*profits?|targets?|tgt|partial)\b/i
const ENTRY_LABEL = /\b(entry|entries|enter|buy\s*zone|sell\s*zone|zone|limit)\b/i
const ENTRY_AT = /@/
const MARKET_LABEL = /\b(now|cmp|market|current\s*market\s*price|current\s*price)\b/i
// Russian field labels (Cyrillic is not ASCII-\w, so these are substring tests).
const STOP_LABEL_RU = /стоп/i
const TARGET_LABEL_RU = /цел|тейк|фикс[а-яё]*\s+прибыл[а-яё]*\s+на/i
const ENTRY_LABEL_RU = /вход/i
const MARKET_RU = /по\s*рынк/i
const HAS_WORD = /[\p{L}]{2,}/u

function isStopLine(line) {
  return STOP_LABEL.test(line) || STOP_LABEL_RU.test(line)
}
function isTargetLine(line) {
  return TARGET_LABEL.test(line) || TARGET_LABEL_RU.test(line)
}
function isEntryLine(line) {
  return ENTRY_LABEL.test(line) || ENTRY_AT.test(line) || ENTRY_LABEL_RU.test(line)
}
function isMarketLine(line) {
  return MARKET_LABEL.test(line) || MARKET_RU.test(line)
}

/** True when the text carries any entry / stop / target field label. */
export function hasTradingLabel(text) {
  return isStopLine(text) || isTargetLine(text) || isEntryLine(text)
}

function messageText(message) {
  return typeof message === 'string' ? message : message?.text || ''
}

function primaryInstrument(clean) {
  return detectInstruments(clean)[0] || null
}

// A worded direction (high confidence) beats an ambiguous emoji; ties break on
// position so the header direction wins.
function primaryDirection(clean) {
  const directions = detectDirections(clean)
  if (directions.length === 0) return null
  return [...directions].sort(
    (a, b) => b.confidence - a.confidence || a.start - b.start
  )[0]
}

function entryFromPrice(price) {
  if (!price) return null
  if (price.type === 'range') {
    return { type: 'range', min: price.min, max: price.max, raw: price.raw }
  }
  return { type: 'single', price: price.value, raw: price.raw }
}

function pushTargets(targets, prices) {
  for (const price of prices) {
    if (price.type === 'range') targets.push(price.min, price.max)
    else targets.push(price.value)
  }
}

// A bare target item under a "Targets/Цели" header: a price with no real words
// (a "1️⃣ 2.5190 💵" line), as opposed to a promo line that merely contains a number.
function isTargetItemLine(line, prices) {
  return prices.length > 0 && !HAS_WORD.test(line)
}

function classifyLine(line, state) {
  const prices = detectPrices(line)
  if (isStopLine(line)) {
    state.collecting = null
    if (state.stopLoss === null && prices.length > 0) {
      state.stopLoss = prices[0].value ?? prices[0].min
    }
    return
  }
  if (isTargetLine(line)) {
    // A "Targets:" / "Цели:" header with no inline price opens collection mode;
    // the levels arrive on the following lines.
    state.collecting = 'targets'
    pushTargets(state.takeProfits, prices)
    return
  }
  if (isEntryLine(line)) {
    state.collecting = null
    if (!state.entry && prices.length > 0) state.entry = entryFromPrice(prices[0])
    else if (prices.length === 0 && isMarketLine(line)) state.marketMarker = true
    return
  }
  if (isMarketLine(line)) {
    state.collecting = null
    state.marketMarker = true
    return
  }
  // While collecting targets, append bare price lines and stop at the first
  // non-target line (e.g. boilerplate / promos).
  if (state.collecting === 'targets') {
    if (isTargetItemLine(line, prices)) {
      pushTargets(state.takeProfits, prices)
      return
    }
    state.collecting = null
  }
  // Unlabelled line: a price next to the instrument/direction header is the entry.
  const isHeader =
    detectInstruments(line).length > 0 || detectDirections(line).length > 0
  if (isHeader && prices.length > 0 && !state.headerEntry) {
    state.headerEntry = entryFromPrice(prices[0])
  }
}

function resolveEntry(state) {
  if (state.entry) return state.entry
  if (state.marketMarker) return null
  return state.headerEntry || null
}

function orderTypeFor(entry) {
  if (!entry) return 'market'
  if (entry.type === 'range') return 'range'
  if (entry.type === 'single') return 'limit'
  return 'unknown'
}

/**
 * @param {import('./types.js').ChatMessage|string} message
 * @returns {Partial<import('./types.js').StructuredSignal>}
 */
export function extractSignalFields(message) {
  const { clean, lines } = normalizeMessageText(messageText(message))
  const instrument = primaryInstrument(clean)
  const direction = primaryDirection(clean)

  const state = {
    entry: null,
    headerEntry: null,
    marketMarker: false,
    stopLoss: null,
    takeProfits: [],
    collecting: null
  }
  for (const line of lines) classifyLine(line, state)

  const entry = resolveEntry(state)
  return {
    instrument: instrument ? instrument.normalized : undefined,
    instrumentRaw: instrument ? instrument.raw : undefined,
    direction: direction ? direction.normalized : undefined,
    orderType: orderTypeFor(entry),
    entry,
    stopLoss: state.stopLoss,
    takeProfits: state.takeProfits
  }
}
