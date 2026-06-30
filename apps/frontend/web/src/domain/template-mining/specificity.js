/* Verasig — Template Mining: template specificity.
   How much literal structure a normalized skeleton carries. Used to order
   accepted rules so the MOST specific family claims a message first, and so a
   generalized (wildcarded) pattern can never outrank a literal one. Inputs are
   always normalized skeletons (template.js), where stray words are already <*>,
   so every bare word token is structural. */

// <*> wildcard, <PLACEHOLDER>, or a structural word (letters/digits).
const TOKEN = /<\*>|<[A-Z_]+>|[\p{L}\p{N}]+/gu

/**
 * @param {string} skeleton normalized template
 * @returns {number} +1 per structural word / value placeholder, −1 per <*>
 */
export function templateSpecificity(skeleton) {
  const tokens = (skeleton || '').match(TOKEN) || []
  let score = 0
  for (const token of tokens) score += token === '<*>' ? -1 : 1
  return score
}
