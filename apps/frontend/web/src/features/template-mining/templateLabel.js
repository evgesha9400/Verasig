/* Verasig — Template Mining: display-only labeling for a template family.
   The miner and the Verify audit both moved server-side; this is only the
   sliver of the old client-side `rules.js` that was ever display logic — a
   family's badge label, and the deterministic id the Verify audit's
   `parserRuleId` resolves back to a family with. The id derivation must stay
   byte-identical to the backend's `compile_rule_from_template` (`rule_<key
   without the tpl_ prefix>`), or accepted families would stop matching their
   own audit rows. */

const ORDER_TYPE_LABEL = {
  market: 'Market',
  limit: 'Limit',
  range: 'Range',
  unknown: 'Signal'
}

// A family's order type spans every instrument in it; describe the FORMAT, not
// a sample symbol, so a multi-instrument family is not mislabelled as one coin.
function dominantOrderType(group) {
  const counts = new Map()
  for (const candidate of group.candidates) {
    const type = candidate.fields.orderType || 'unknown'
    counts.set(type, (counts.get(type) || 0) + 1)
  }
  const [type] = [...counts].reduce(
    (best, entry) => (entry[1] > best[1] ? entry : best),
    ['market', -1]
  )
  return type
}

function presentFields(group) {
  const candidates = group.candidates
  return {
    entry: candidates.some((candidate) => Boolean(candidate.fields.entry)),
    stopLoss: candidates.some((candidate) => candidate.fields.stopLoss != null),
    takeProfits: candidates.some(
      (candidate) =>
        Array.isArray(candidate.fields.takeProfits) &&
        candidate.fields.takeProfits.length > 0
    )
  }
}

export function formatLabel(group) {
  const present = presentFields(group)
  const parts = ['direction']
  if (present.entry) parts.push('entry')
  if (present.stopLoss) parts.push('SL')
  if (present.takeProfits) parts.push('TP')
  return `${ORDER_TYPE_LABEL[dominantOrderType(group)]} signal · ${parts.join(' + ')}`
}

// Mirrors the backend's `compile_rule_from_template` id derivation exactly —
// the Verify audit's `parsedSignals[].parserRuleId` is computed server-side
// from the same templateKey and must resolve back to this family.
export function templateRuleId(templateKey) {
  return `rule_${templateKey.replace(/^tpl_/, '')}`
}

// One display record per accepted family: what the Verify audit's Template
// filter and its per-row template badge show.
export function describeAcceptedTemplates(acceptedGroups) {
  return acceptedGroups.map((group) => ({
    id: templateRuleId(group.templateKey),
    templateKey: group.templateKey,
    name: formatLabel(group)
  }))
}
