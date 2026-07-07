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
  // key on presence, not truthiness, so a legitimately falsy built value
  // (empty/0/'') is still cached instead of rebuilt every call.
  if (!cache.has(key)) {
    cache.set(key, build())
  }
  return cache.get(key)
}
