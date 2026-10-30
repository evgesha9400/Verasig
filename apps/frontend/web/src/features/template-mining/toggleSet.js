/* Verasig — Template Mining: expand/collapse id set toggling.
   Shared by every "which rows are expanded" state in this feature (the audit's
   row detail, the family grid's message list) — a key toggles into or out of
   the open set, immutably, for React state setters. */

/**
 * @template T
 * @param {ReadonlySet<T>} set
 * @param {T} key
 * @returns {Set<T>}
 */
export function toggleInSet(set, key) {
  const next = new Set(set)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  return next
}
