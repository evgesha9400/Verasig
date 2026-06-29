/* Verasig — Template Mining: instrument detection.
   Three layers, most specific first: a curated alias dictionary, generic crypto
   base/quote pairs, then forex six-letter pairs gated by known currency codes.
   Aliases normalize to one canonical symbol so "GOLD" and "XAU" group together.

   Dictionaries are intentionally data, not code — channel- or broker-specific
   symbols extend the maps below without touching the matching logic. */

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

const DICTIONARY_CONFIDENCE = 0.95
const PAIR_CONFIDENCE = 0.85

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// `\b` fails before symbols like "&" or "/", so bound matches with explicit
// non-alphanumeric lookarounds that still treat the edge of the string as a boundary.
function aliasMatcher(term) {
  return new RegExp(`(?<![A-Za-z0-9])${escapeRegExp(term)}(?![A-Za-z0-9])`, 'gi')
}

function buildAliasRules() {
  const rules = []
  for (const [normalized, terms] of Object.entries(ALIASES)) {
    for (const term of terms) {
      rules.push({ matcher: aliasMatcher(term), normalized })
    }
  }
  // Longer aliases first so "BTCUSDT" wins over the "BTC" substring rule.
  return rules.sort((a, b) => b.matcher.source.length - a.matcher.source.length)
}

const ALIAS_RULES = buildAliasRules()
const CRYPTO_PAIR = new RegExp(
  `(?<![A-Za-z0-9])([A-Z]{2,6})\\s*/\\s*(${CRYPTO_QUOTES.join('|')})(?![A-Za-z0-9])`,
  'gi'
)
const FOREX_PAIR = /(?<![A-Za-z0-9])([A-Za-z]{3})([A-Za-z]{3})(?![A-Za-z0-9])/g

function pushHit(hits, start, end, normalized, raw, confidence) {
  hits.push({ start, end, normalized, raw, confidence })
}

function collectAliasHits(text, hits) {
  for (const rule of ALIAS_RULES) {
    rule.matcher.lastIndex = 0
    let match
    while ((match = rule.matcher.exec(text)) !== null) {
      pushHit(
        hits,
        match.index,
        match.index + match[0].length,
        rule.normalized,
        match[0],
        DICTIONARY_CONFIDENCE
      )
    }
  }
}

function collectCryptoPairHits(text, hits) {
  let match
  CRYPTO_PAIR.lastIndex = 0
  while ((match = CRYPTO_PAIR.exec(text)) !== null) {
    const normalized = `${match[1]}${match[2]}`.toUpperCase()
    pushHit(
      hits,
      match.index,
      match.index + match[0].length,
      normalized,
      match[0],
      PAIR_CONFIDENCE
    )
  }
}

function collectForexPairHits(text, hits) {
  let match
  FOREX_PAIR.lastIndex = 0
  while ((match = FOREX_PAIR.exec(text)) !== null) {
    const base = match[1].toUpperCase()
    const quote = match[2].toUpperCase()
    if (!CURRENCY_CODES.has(base) || !CURRENCY_CODES.has(quote)) continue
    pushHit(
      hits,
      match.index,
      match.index + match[0].length,
      `${base}${quote}`,
      match[0],
      PAIR_CONFIDENCE
    )
  }
}

function overlaps(hit, accepted) {
  return accepted.some((other) => hit.start < other.end && other.start < hit.end)
}

// Earliest span wins; later overlapping or duplicate-symbol hits are dropped so
// each symbol surfaces once.
function dedupeHits(hits) {
  const ordered = [...hits].sort((a, b) => a.start - b.start || b.end - a.end)
  const accepted = []
  const seenSymbols = new Set()
  for (const hit of ordered) {
    if (seenSymbols.has(hit.normalized)) continue
    if (overlaps(hit, accepted)) continue
    accepted.push(hit)
    seenSymbols.add(hit.normalized)
  }
  return accepted
}

/**
 * @param {string} text
 * @returns {import('./types.js').DetectedEntity[]}
 */
export function detectInstruments(text) {
  if (!text) return []
  const hits = []
  collectAliasHits(text, hits)
  collectCryptoPairHits(text, hits)
  collectForexPairHits(text, hits)
  return dedupeHits(hits).map((hit) => ({
    raw: hit.raw,
    normalized: hit.normalized,
    start: hit.start,
    end: hit.end,
    confidence: hit.confidence
  }))
}
