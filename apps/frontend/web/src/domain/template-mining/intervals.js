/* Verasig — Template Mining: half-open interval overlap test.
   Shared by instrument and price-span dedupe, which each reserve character
   ranges and need to know when two of them collide. */

/**
 * @returns {boolean} true when [aStart, aEnd) and [bStart, bEnd) intersect
 */
export function intervalsOverlap(aStart, aEnd, bStart, bEnd) {
  return aStart < bEnd && bStart < aEnd
}

/**
 * @param {number} start
 * @param {number} end
 * @param {ReadonlyArray<T>} spans
 * @param {(span: T) => [number, number]} [spanOf] extracts [start, end] from a span
 * @returns {boolean} true when [start, end) overlaps any span in the list
 * @template T
 */
export function overlapsAny(start, end, spans, spanOf = (span) => span) {
  return spans.some((span) => {
    const [spanStart, spanEnd] = spanOf(span)
    return intervalsOverlap(start, end, spanStart, spanEnd)
  })
}

// Earliest span first; ties broken longest-first, so a dedupe pass that keeps
// only the first non-overlapping span per start position prefers the one
// covering the most text.
export function byStartThenLongest(a, b) {
  return a.start - b.start || b.end - a.end
}
