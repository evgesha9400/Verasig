/* Verasig — Template Mining: message text normalization.
   Cleans Telegram text for deterministic detection while keeping the original
   for display. Each transform is one named step; `normalizeMessageText`
   assembles them. */

const UNICODE_SPACES = /[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000\uFEFF]/g
const DASHES = /[\u2010-\u2015\u2212]/g // hyphen, en/em dashes, minus
const THOUSANDS = /(\d),(?=\d{3}(?:\D|$))/g

function unifyUnicodeSpaces(text) {
  return text.replace(UNICODE_SPACES, ' ')
}

function unifyDashes(text) {
  return text.replace(DASHES, '-')
}

function stripThousandsSeparators(text) {
  let previous
  let current = text
  do {
    previous = current
    current = current.replace(THOUSANDS, '$1')
  } while (current !== previous)
  return current
}

export function toCleanLines(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.replace(/[ \t]+/g, ' ').trim())
    .filter((line) => line.length > 0)
}

/** Escape regex metacharacters so a literal string can be embedded in a pattern. */
export function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * @param {string} text
 * @returns {import('./types.js').NormalizedText}
 */
export function normalizeMessageText(text) {
  const original = typeof text === 'string' ? text : ''
  const unified = stripThousandsSeparators(unifyDashes(unifyUnicodeSpaces(original)))
  const lines = toCleanLines(unified)
  const clean = lines.join('\n')
  return { original, clean, lower: clean.toLowerCase(), lines }
}
