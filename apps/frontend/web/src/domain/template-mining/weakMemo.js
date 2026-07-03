/* Verasig — Template Mining: per-key lazy cache.
   Overlay-derived rule lists and per-rule matchers are fixed once their key
   (the overlay, the rule) is unchanged, so compiling them once and caching by
   that key avoids redoing the work for every message/candidate. */

/**
 * @template K, V
 * @param {WeakMap<K, V>} cache
 * @param {K} key
 * @param {() => V} build
 * @returns {V}
 */
export function weakMemo(cache, key, build) {
  let value = cache.get(key)
  if (!value) {
    value = build()
    cache.set(key, value)
  }
  return value
}
