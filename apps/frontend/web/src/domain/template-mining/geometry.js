/* Verasig — Template Mining: price-geometry validation.
   A BUY's stop sits below and targets above the entry; a SELL is the mirror. When
   there is no entry we fall back to the stop-vs-targets relationship. Violations
   never hard-reject — they lower confidence and raise a warning so the family is
   sent to review rather than silently dropped. */

const VALID_BONUS = 2
const VIOLATION_PENALTY = -3

const ISSUE = {
  STOP_LOSS_ON_WRONG_SIDE: 'stop_loss_on_wrong_side',
  TAKE_PROFIT_ON_WRONG_SIDE: 'take_profit_on_wrong_side',
  STOP_LOSS_NOT_BELOW_TARGETS: 'stop_loss_not_below_targets',
  STOP_LOSS_NOT_ABOVE_TARGETS: 'stop_loss_not_above_targets'
}

function resolveFields(input) {
  return input && input.fields ? input.fields : input || {}
}

// A range entry is two bounds, not a midpoint: a BUY's stop must sit below the
// WHOLE zone and its targets above it, so a level inside the band is a violation.
function entryBounds(entry) {
  if (!entry) return null
  if (entry.type === 'range') return { low: entry.min, high: entry.max }
  if (typeof entry.price === 'number') return { low: entry.price, high: entry.price }
  return null
}

function sideLabel(direction) {
  return direction === 'BUY' ? 'LONG' : 'SHORT'
}

function relationToEntry(value, bounds) {
  if (value < bounds.low) return 'below'
  if (value > bounds.high) return 'above'
  if (bounds.low === bounds.high) return 'equal'
  return 'inside'
}

function stopLossEntryLabel(direction, relation) {
  if (relation === 'equal') return 'Stop loss equals entry'
  if (relation === 'inside') {
    return `Stop loss inside entry range for ${sideLabel(direction)}`
  }
  return direction === 'BUY'
    ? 'Stop loss above entry for LONG'
    : 'Stop loss below entry for SHORT'
}

function takeProfitEntryLabel(direction, relation) {
  if (relation === 'equal') return 'Take profit equals entry'
  if (relation === 'inside') {
    return `Take profit inside entry range for ${sideLabel(direction)}`
  }
  return direction === 'BUY'
    ? 'Take profit below entry for LONG'
    : 'Take profit above entry for SHORT'
}

function stopLossEntryIssue(direction, bounds, stopLoss) {
  const label = stopLossEntryLabel(direction, relationToEntry(stopLoss, bounds))
  const expected = direction === 'BUY' ? 'below' : 'above'
  return {
    code: ISSUE.STOP_LOSS_ON_WRONG_SIDE,
    field: 'stopLoss',
    label,
    message: `${label}. Stop loss should sit ${expected} entry for a ${sideLabel(direction)}.`,
    price: stopLoss
  }
}

function takeProfitEntryIssue(direction, bounds, target) {
  const label = takeProfitEntryLabel(direction, relationToEntry(target, bounds))
  const expected = direction === 'BUY' ? 'above' : 'below'
  return {
    code: ISSUE.TAKE_PROFIT_ON_WRONG_SIDE,
    field: 'takeProfits',
    label,
    message: `${label}. Take profit should sit ${expected} entry for a ${sideLabel(direction)}.`,
    price: target
  }
}

function stopLossTargetIssue(direction, stopLoss) {
  const isBuy = direction === 'BUY'
  const label = isBuy
    ? 'Stop loss not below take profits for LONG'
    : 'Stop loss not above take profits for SHORT'
  const expected = isBuy ? 'below' : 'above'
  return {
    code: isBuy ? ISSUE.STOP_LOSS_NOT_BELOW_TARGETS : ISSUE.STOP_LOSS_NOT_ABOVE_TARGETS,
    field: 'stopLoss',
    label,
    message: `${label}. Stop loss should sit ${expected} take profits for a ${sideLabel(direction)}.`,
    price: stopLoss
  }
}

function checkAgainstEntry(direction, bounds, stopLoss, takeProfits, issues) {
  const isBuy = direction === 'BUY'
  if (stopLoss !== null && stopLoss !== undefined) {
    const stopOk = isBuy ? stopLoss < bounds.low : stopLoss > bounds.high
    if (!stopOk) issues.push(stopLossEntryIssue(direction, bounds, stopLoss))
  }
  for (const target of takeProfits) {
    const targetOk = isBuy ? target > bounds.high : target < bounds.low
    if (!targetOk) issues.push(takeProfitEntryIssue(direction, bounds, target))
  }
}

function checkStopVsTargets(direction, stopLoss, takeProfits, issues) {
  if (direction === 'BUY' && stopLoss >= Math.min(...takeProfits)) {
    issues.push(stopLossTargetIssue(direction, stopLoss))
  }
  if (direction === 'SELL' && stopLoss <= Math.max(...takeProfits)) {
    issues.push(stopLossTargetIssue(direction, stopLoss))
  }
}

/**
 * @param {import('./types.js').Candidate|Partial<import('./types.js').StructuredSignal>} input
 * @returns {{isValid: boolean, warnings: string[], issues: object[], scoreAdjustment: number}}
 */
export function validatePriceGeometry(input) {
  const fields = resolveFields(input)
  const direction = fields.direction
  const stopLoss = fields.stopLoss ?? null
  const takeProfits = Array.isArray(fields.takeProfits) ? fields.takeProfits : []
  const bounds = entryBounds(fields.entry)
  const issues = []

  const canCheckAgainstEntry =
    bounds !== null && (stopLoss !== null || takeProfits.length > 0)
  const canCheckStopVsTargets =
    bounds === null && stopLoss !== null && takeProfits.length > 0

  if (!direction || (!canCheckAgainstEntry && !canCheckStopVsTargets)) {
    return { isValid: true, warnings: [], issues: [], scoreAdjustment: 0 }
  }

  if (canCheckAgainstEntry) {
    checkAgainstEntry(direction, bounds, stopLoss, takeProfits, issues)
  } else {
    checkStopVsTargets(direction, stopLoss, takeProfits, issues)
  }

  const isValid = issues.length === 0
  return {
    isValid,
    warnings: issues.map((issue) => issue.message),
    issues,
    scoreAdjustment: isValid ? VALID_BONUS : VIOLATION_PENALTY
  }
}
