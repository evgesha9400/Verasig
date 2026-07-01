/* Verasig — Template Mining: direction detection.
   Words carry strong confidence; direction emojis are deliberately weak because
   a coloured circle is ambiguous out of context. Both are returned in source
   order so the scorer can tell "emoji-only" signals apart from worded ones. */

import { escapeRegExp } from './text.js'

const WORD_CONFIDENCE = 0.9
const EMOJI_CONFIDENCE = 0.4
// Below word strength — the boundary the scorer/normalizer use to tell an
// emoji-inferred direction apart from one the author actually wrote out.
const EMOJI_CONFIDENCE_CEILING = 0.7

const BUY_WORDS = ['buy', 'long', 'bullish', 'call', 'calls']
const SELL_WORDS = ['sell', 'short', 'bearish', 'put', 'puts']
// Russian: лонг = long/buy, шорт = short/sell.
const BUY_WORDS_RU = ['лонг']
const SELL_WORDS_RU = ['шорт']
const BUY_EMOJIS = ['🟢', '⬆', '🚀', '📈', '🔼']
const SELL_EMOJIS = ['🔴', '⬇', '📉', '🔽']

/** @param {import('./types.js').DetectedEntity} entity */
export function isEmojiDirection(entity) {
  return entity.confidence < EMOJI_CONFIDENCE_CEILING
}

/** @param {import('./types.js').DetectedEntity[]} directions */
export function isEmojiOnlyDirection(directions) {
  return directions.length > 0 && directions.every(isEmojiDirection)
}

function wordMatcher(words) {
  return new RegExp(`\\b(${words.join('|')})\\b`, 'gi')
}

// `\b` is ASCII-only, so bound Cyrillic words with Unicode letter lookarounds.
function cyrillicMatcher(words) {
  return new RegExp(`(?<!\\p{L})(${words.join('|')})(?!\\p{L})`, 'giu')
}

function emojiMatcher(emojis) {
  // Optional VS16 (U+FE0F) lets "⬆️" match the same rule as bare "⬆".
  return new RegExp(`(${emojis.join('|')})️?`, 'g')
}

// A taught token: letter-bounded when alphabetic (so "up" doesn't hit "upset"),
// raw when it's an emoji/symbol. Word strength, so it isn't treated as emoji-only.
function tokenMatcher(token) {
  const body = escapeRegExp(token)
  return /^[\p{L}]+$/u.test(token)
    ? new RegExp(`(?<!\\p{L})${body}(?!\\p{L})`, 'giu')
    : new RegExp(body, 'g')
}

function overlayDirectionRules(overlay) {
  const tokens = overlay?.directionTokens
  if (!tokens) return []
  return Object.entries(tokens).map(([token, normalized]) => ({
    matcher: tokenMatcher(token),
    normalized,
    confidence: WORD_CONFIDENCE
  }))
}

const RULES = [
  { matcher: wordMatcher(BUY_WORDS), normalized: 'BUY', confidence: WORD_CONFIDENCE },
  { matcher: wordMatcher(SELL_WORDS), normalized: 'SELL', confidence: WORD_CONFIDENCE },
  {
    matcher: cyrillicMatcher(BUY_WORDS_RU),
    normalized: 'BUY',
    confidence: WORD_CONFIDENCE
  },
  {
    matcher: cyrillicMatcher(SELL_WORDS_RU),
    normalized: 'SELL',
    confidence: WORD_CONFIDENCE
  },
  {
    matcher: emojiMatcher(BUY_EMOJIS),
    normalized: 'BUY',
    confidence: EMOJI_CONFIDENCE
  },
  {
    matcher: emojiMatcher(SELL_EMOJIS),
    normalized: 'SELL',
    confidence: EMOJI_CONFIDENCE
  }
]

// Compiling overlay-token regexes is wasted work once the overlay is unchanged
// (it is the same object for every message in a mining run) — cache per overlay.
const overlayRulesCache = new WeakMap()

function rulesFor(overlay) {
  if (!overlay?.directionTokens) return RULES
  let rules = overlayRulesCache.get(overlay)
  if (!rules) {
    rules = [...RULES, ...overlayDirectionRules(overlay)]
    overlayRulesCache.set(overlay, rules)
  }
  return rules
}

/**
 * @param {string} text
 * @param {object} overlay
 * @returns {import('./types.js').DetectedEntity[]}
 */
export function detectDirections(text, overlay = {}) {
  if (!text) return []
  const rules = rulesFor(overlay)
  const hits = []
  for (const rule of rules) {
    rule.matcher.lastIndex = 0
    let match
    while ((match = rule.matcher.exec(text)) !== null) {
      hits.push({
        raw: match[0],
        normalized: rule.normalized,
        start: match.index,
        end: match.index + match[0].length,
        confidence: rule.confidence
      })
    }
  }
  return hits.sort((a, b) => a.start - b.start)
}
