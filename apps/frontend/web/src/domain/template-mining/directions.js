/* Verasig — Template Mining: direction detection.
   Words carry strong confidence; direction emojis are deliberately weak because
   a coloured circle is ambiguous out of context. Both are returned in source
   order so the scorer can tell "emoji-only" signals apart from worded ones. */

const WORD_CONFIDENCE = 0.9
const EMOJI_CONFIDENCE = 0.4

const BUY_WORDS = ['buy', 'long', 'bullish', 'call', 'calls']
const SELL_WORDS = ['sell', 'short', 'bearish', 'put', 'puts']
// Russian: лонг = long/buy, шорт = short/sell.
const BUY_WORDS_RU = ['лонг']
const SELL_WORDS_RU = ['шорт']
const BUY_EMOJIS = ['🟢', '⬆', '🚀', '📈', '🔼']
const SELL_EMOJIS = ['🔴', '⬇', '📉', '🔽']

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

/**
 * @param {string} text
 * @returns {import('./types.js').DetectedEntity[]}
 */
export function detectDirections(text) {
  if (!text) return []
  const hits = []
  for (const rule of RULES) {
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
