/* Verasig — Template Mining: pattern subsumption.
   Does an accepted rule's pattern match a message skeleton, allowing it to be
   MORE general than the message? Used by the audit to let a general accepted
   family recover messages that exactly match no accepted family. Matching is
   one-directional (pattern ⊇ message) and structural: same lines, same token
   count per line, each pattern token matching its message token. */

// <*> wildcard, <PLACEHOLDER>, or a structural word.
const TOKEN = /<\*>|<[A-Z_]+>|[\p{L}\p{N}]+/gu

// A general placeholder (key) matches the more-specific placeholders it covers.
// One-directional: <PRICE_LIST> covers <PRICE>, but not the reverse. <RANGE> is
// kept distinct from <PRICE> — a zone entry is not a single level.
const SUBSUMES = {
  '<PRICE_LIST>': new Set(['<PRICE>']),
  '<SIDE>': new Set(['<SIDE_EMOJI>'])
}

function tokenize(line) {
  return line.match(TOKEN) || []
}

// A <*> absorbs any single token; a placeholder matches itself or one it covers;
// a literal word matches only the identical word.
function tokenSubsumes(patternToken, messageToken) {
  if (patternToken === '<*>') return true
  if (patternToken === messageToken) return true
  return SUBSUMES[patternToken]?.has(messageToken) ?? false
}

function lineSubsumes(patternLine, messageLine) {
  const patternTokens = tokenize(patternLine)
  const messageTokens = tokenize(messageLine)
  if (patternTokens.length !== messageTokens.length) return false
  return patternTokens.every((token, index) =>
    tokenSubsumes(token, messageTokens[index])
  )
}

/**
 * @param {string} pattern accepted rule's normalized template
 * @param {string} message candidate's normalized template
 * @returns {boolean} true when the pattern matches (covers) the message
 */
export function patternSubsumes(pattern, message) {
  const patternLines = (pattern || '').split('\n')
  const messageLines = (message || '').split('\n')
  if (patternLines.length !== messageLines.length) return false
  return patternLines.every((line, index) => lineSubsumes(line, messageLines[index]))
}
