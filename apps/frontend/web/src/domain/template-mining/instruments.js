/* Verasig — Template Mining: instrument detection.
   Three layers, most specific first: a curated alias dictionary, generic crypto
   base/quote pairs, then forex six-letter pairs gated by known currency codes.
   Aliases normalize to one canonical symbol so "GOLD" and "XAU" group together.

   Dictionaries are intentionally data, not code — channel- or broker-specific
   symbols extend the maps below without touching the matching logic. */

import { escapeRegExp } from './text.js'
import { byStartThenLongest, overlapsAny } from './intervals.js'
import { weakMemo } from './weakMemo.js'

const CURRENCY_CODES = new Set(['AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'JPY', 'NZD', 'USD'])

const CRYPTO_QUOTES = ['USDT', 'USDC', 'USD', 'PERP', 'BTC', 'ETH']

// canonical symbol -> alias terms that should normalize to it.
const ALIASES = {
  XAUUSD: ['XAUUSD', 'XAU', 'GOLD'],
  XAGUSD: ['XAGUSD', 'XAG', 'SILVER'],
  EURUSD: ['EURUSD'],
  GBPUSD: ['GBPUSD'],
  USDJPY: ['USDJPY'],
  GBPJPY: ['GBPJPY'],
  AUDUSD: ['AUDUSD'],
  USDCAD: ['USDCAD'],
  USDCHF: ['USDCHF'],
  NZDUSD: ['NZDUSD'],
  EURJPY: ['EURJPY'],
  EURGBP: ['EURGBP'],
  BTCUSDT: ['BTCUSDT', 'BTCUSD', 'BITCOIN', 'BTC'],
  ETHUSDT: ['ETHUSDT', 'ETHUSD', 'ETHEREUM', 'ETH'],
  SOLUSDT: ['SOLUSDT', 'SOL'],
  NAS100: ['NAS100', 'NASDAQ', 'US100'],
  US30: ['US30', 'DOW'],
  SPX500: ['SPX500', 'SP500', 'S&P500', 'SPX'],
  GER40: ['GER40', 'DAX'],
  AAPL: ['AAPL'],
  TSLA: ['TSLA'],
  NVDA: ['NVDA'],
  MSFT: ['MSFT']
}

// Bare crypto bases seen in real channels — matched case-sensitively (uppercase)
// so ordinary words like "Link" do not register as instruments.
const CRYPTO_TICKERS = new Set([
  'XRP',
  'DOGE',
  'BNB',
  'ADA',
  'AVAX',
  'LINK',
  'DOT',
  'MATIC',
  'POL',
  'TRX',
  'LTC',
  'BCH',
  'ATOM',
  'UNI',
  'TON',
  'SUI',
  'TIA',
  'WIF',
  'ORDI',
  'SEI',
  'ARB',
  'OP',
  'INJ',
  'NEAR',
  'PEPE',
  'SHIB',
  'BONK',
  'FLOKI',
  'APT',
  'FIL',
  'AAVE',
  'RNDR',
  'RENDER',
  'FET',
  'ICP',
  'HBAR',
  'XLM',
  'ALGO',
  'EGLD',
  'SAND',
  'MANA',
  'AXS',
  'GALA',
  'FARTCOIN',
  'NOT',
  'JUP',
  'PYTH',
  'WLD',
  'ENA',
  'ONDO'
])

const DICTIONARY_CONFIDENCE = 0.95
const PAIR_CONFIDENCE = 0.85

// Russian "Монета:/Монету:" coin label → the ticker that follows. The `d` flag
// exposes the capture-group span so only the ticker (not the label) is replaced.
// Allow a #/$ prefix and digits in the ticker so "#1INCH" / "1000PEPE" are caught.
const COIN_LABEL = /Монет[а-яё]*\s*:?\s*[#$]?([A-Za-z0-9]{2,10})/dgiu
const BARE_TICKER = /(?<![A-Za-z0-9])([A-Z]{2,8})(?![A-Za-z0-9])/g
const HAS_LETTER = /[A-Za-z]/

function toUsdt(ticker) {
  const upper = ticker.toUpperCase()
  return upper.endsWith('USDT') ? upper : `${upper}USDT`
}

// `\b` fails before symbols like "&" or "/", so bound matches with explicit
// non-alphanumeric lookarounds that still treat the edge of the string as a boundary.
function aliasMatcher(term) {
  return new RegExp(`(?<![A-Za-z0-9])${escapeRegExp(term)}(?![A-Za-z0-9])`, 'gi')
}

// Longer aliases first so "BTCUSDT" wins over the "BTC" substring rule.
function byLongestMatcherFirst(a, b) {
  return b.matcher.source.length - a.matcher.source.length
}

function buildAliasRules() {
  const rules = []
  for (const [normalized, terms] of Object.entries(ALIASES)) {
    for (const term of terms) {
      rules.push({ matcher: aliasMatcher(term), normalized })
    }
  }
  return rules.sort(byLongestMatcherFirst)
}

const ALIAS_RULES = buildAliasRules()
const CRYPTO_PAIR = new RegExp(
  `(?<![A-Za-z0-9])([A-Za-z0-9]{2,8})\\s*/\\s*(${CRYPTO_QUOTES.join('|')})(?![A-Za-z0-9])`,
  'gi'
)
const FOREX_PAIR = /(?<![A-Za-z0-9])([A-Za-z]{3})([A-Za-z]{3})(?![A-Za-z0-9])/g

function collectAliasHits(text, hits, rules) {
  for (const rule of rules) {
    rule.matcher.lastIndex = 0
    let match
    while ((match = rule.matcher.exec(text)) !== null) {
      hits.push({
        start: match.index,
        end: match.index + match[0].length,
        normalized: rule.normalized,
        raw: match[0],
        confidence: DICTIONARY_CONFIDENCE
      })
    }
  }
}

// Overlay aliases (user-taught alias -> canonical symbol) join the built-in
// rules, longest-term first so specific aliases win the overlap dedupe.
// Compiling + sorting is wasted work once the overlay is unchanged (it is the
// same object for every message in a mining run) — cache per overlay.
const overlayAliasRulesCache = new WeakMap()

function aliasRulesWith(overlay) {
  const aliases = overlay?.instrumentAliases
  if (!aliases || Object.keys(aliases).length === 0) return ALIAS_RULES
  return weakMemo(overlayAliasRulesCache, overlay, () => {
    const extra = Object.entries(aliases).map(([term, normalized]) => ({
      matcher: aliasMatcher(term),
      normalized
    }))
    return [...extra, ...ALIAS_RULES].sort(byLongestMatcherFirst)
  })
}

function collectCryptoPairHits(text, hits) {
  let match
  CRYPTO_PAIR.lastIndex = 0
  while ((match = CRYPTO_PAIR.exec(text)) !== null) {
    const base = match[1].toUpperCase()
    const quote = match[2].toUpperCase()
    // A fiat base, a numbers-only base, or base === quote is not a real pair.
    if (base === quote || CURRENCY_CODES.has(base) || !HAS_LETTER.test(base)) continue
    hits.push({
      start: match.index,
      end: match.index + match[0].length,
      normalized: `${base}${quote}`,
      raw: match[0],
      confidence: PAIR_CONFIDENCE
    })
  }
}

function collectForexPairHits(text, hits) {
  let match
  FOREX_PAIR.lastIndex = 0
  while ((match = FOREX_PAIR.exec(text)) !== null) {
    const base = match[1].toUpperCase()
    const quote = match[2].toUpperCase()
    if (!CURRENCY_CODES.has(base) || !CURRENCY_CODES.has(quote)) continue
    if (base === quote) continue // USDUSD is not a pair
    hits.push({
      start: match.index,
      end: match.index + match[0].length,
      normalized: `${base}${quote}`,
      raw: match[0],
      confidence: PAIR_CONFIDENCE
    })
  }
}

function collectCoinLabelHits(text, hits) {
  let match
  COIN_LABEL.lastIndex = 0
  while ((match = COIN_LABEL.exec(text)) !== null) {
    if (!HAS_LETTER.test(match[1])) continue // skip "Монета: 100" style numerics
    const [start, end] = match.indices[1]
    hits.push({
      start,
      end,
      normalized: toUsdt(match[1]),
      raw: match[1],
      confidence: DICTIONARY_CONFIDENCE
    })
  }
}

function collectBareTickerHits(text, hits) {
  let match
  BARE_TICKER.lastIndex = 0
  while ((match = BARE_TICKER.exec(text)) !== null) {
    if (!CRYPTO_TICKERS.has(match[1])) continue
    hits.push({
      start: match.index,
      end: match.index + match[0].length,
      normalized: toUsdt(match[1]),
      raw: match[1],
      confidence: PAIR_CONFIDENCE
    })
  }
}

// Earliest span wins; later overlapping or duplicate-symbol hits are dropped so
// each symbol surfaces once.
function dedupeHits(hits) {
  const ordered = [...hits].sort(byStartThenLongest)
  const accepted = []
  const seenSymbols = new Set()
  for (const hit of ordered) {
    if (seenSymbols.has(hit.normalized)) continue
    if (overlapsAny(hit.start, hit.end, accepted, (h) => [h.start, h.end])) continue
    accepted.push(hit)
    seenSymbols.add(hit.normalized)
  }
  return accepted
}

/**
 * @param {string} text
 * @param {object} overlay
 * @returns {import('./types.js').DetectedEntity[]}
 */
export function detectInstruments(text, overlay = {}) {
  if (!text) return []
  const hits = []
  collectAliasHits(text, hits, aliasRulesWith(overlay))
  collectCoinLabelHits(text, hits)
  collectCryptoPairHits(text, hits)
  collectForexPairHits(text, hits)
  collectBareTickerHits(text, hits)
  return dedupeHits(hits).map((hit) => ({
    raw: hit.raw,
    normalized: hit.normalized,
    start: hit.start,
    end: hit.end,
    confidence: hit.confidence
  }))
}
