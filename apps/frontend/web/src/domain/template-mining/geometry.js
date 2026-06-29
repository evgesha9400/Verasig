/* Verasig — Template Mining: price-geometry validation.
   A BUY's stop sits below and targets above the entry; a SELL is the mirror. When
   there is no entry we fall back to the stop-vs-targets relationship. Violations
   never hard-reject — they lower confidence and raise a warning so the family is
   sent to review rather than silently dropped. */

const VALID_BONUS = 2
const VIOLATION_PENALTY = -3

function resolveFields(input) {
  return input && input.fields ? input.fields : input || {}
}

function entryReference(entry) {
  if (!entry) return null
  if (entry.type === 'range') return (entry.min + entry.max) / 2
  if (typeof entry.price === 'number') return entry.price
  return null
}

function checkAgainstEntry(direction, reference, stopLoss, takeProfits, warnings) {
  const wantsAbove = direction === 'BUY'
  if (stopLoss !== null && stopLoss !== undefined) {
    const stopBelow = stopLoss < reference
    if (stopBelow !== wantsAbove) {
      warnings.push(`Stop loss is on the wrong side of entry for a ${direction}.`)
    }
  }
  for (const target of takeProfits) {
    const targetAbove = target > reference
    if (targetAbove !== wantsAbove) {
      warnings.push(
        `Take profit ${target} is on the wrong side of entry for a ${direction}.`
      )
    }
  }
}

function checkStopVsTargets(direction, stopLoss, takeProfits, warnings) {
  if (direction === 'BUY' && stopLoss >= Math.min(...takeProfits)) {
    warnings.push('Stop loss is not below the targets for a BUY.')
  }
  if (direction === 'SELL' && stopLoss <= Math.max(...takeProfits)) {
    warnings.push('Stop loss is not above the targets for a SELL.')
  }
}

/**
 * @param {import('./types.js').Candidate|Partial<import('./types.js').StructuredSignal>} input
 * @returns {{isValid: boolean, warnings: string[], scoreAdjustment: number}}
 */
export function validatePriceGeometry(input) {
  const fields = resolveFields(input)
  const direction = fields.direction
  const stopLoss = fields.stopLoss ?? null
  const takeProfits = Array.isArray(fields.takeProfits) ? fields.takeProfits : []
  const reference = entryReference(fields.entry)
  const warnings = []

  const canCheckAgainstEntry =
    reference !== null && (stopLoss !== null || takeProfits.length > 0)
  const canCheckStopVsTargets =
    reference === null && stopLoss !== null && takeProfits.length > 0

  if (!direction || (!canCheckAgainstEntry && !canCheckStopVsTargets)) {
    return { isValid: true, warnings: [], scoreAdjustment: 0 }
  }

  if (canCheckAgainstEntry) {
    checkAgainstEntry(direction, reference, stopLoss, takeProfits, warnings)
  } else {
    checkStopVsTargets(direction, stopLoss, takeProfits, warnings)
  }

  const isValid = warnings.length === 0
  return {
    isValid,
    warnings,
    scoreAdjustment: isValid ? VALID_BONUS : VIOLATION_PENALTY
  }
}
