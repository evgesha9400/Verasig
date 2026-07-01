/* Verasig — Template Mining: half-open interval overlap test.
   Shared by instrument and price-span dedupe, which each reserve character
   ranges and need to know when two of them collide. */

/**
 * @returns {boolean} true when [aStart, aEnd) and [bStart, bEnd) intersect
 */
export function intervalsOverlap(aStart, aEnd, bStart, bEnd) {
  return aStart < bEnd && bStart < aEnd
}
