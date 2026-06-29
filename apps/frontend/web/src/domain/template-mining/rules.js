/* Verasig — Template Mining: deterministic parser rules.
   An accepted template family compiles into an inspectable ParserRule. Running
   the rule set over the full history sorts every message into one audit bucket:
   a parsed signal, an ambiguous candidate, a rejected update/result, a rare
   unaccepted format, or a partial-evidence potential miss. No LLM is involved. */

import { detectInstruments } from './instruments.js'
import { detectDirections } from './directions.js'
import { detectPrices } from './prices.js'
import { hasTradingLabel } from './fields.js'
import { normalizeMessageText } from './text.js'
import { attemptExtractSignal } from './extract.js'
import { mineTemplateGroups } from './mining.js'

const REJECT_PHRASES = [
  'hit tp',
  'tp hit',
  'sl hit',
  'closed',
  'close',
  'move sl',
  'move stop',
  'breakeven',
  'break even',
  'cancel',
  'running',
  'pips'
]
const NON_SIGNAL_INTENTS = new Set(['update', 'result', 'commentary'])
const PARSEABLE_INTENTS = new Set(['new_signal', 'unknown'])

function dominantInstrument(group) {
  const counts = new Map()
  for (const candidate of group.candidates) {
    const symbol = candidate.fields.instrument
    if (symbol) counts.set(symbol, (counts.get(symbol) || 0) + 1)
  }
  let best = null
  let bestCount = 0
  for (const [symbol, count] of counts) {
    if (count > bestCount) {
      best = symbol
      bestCount = count
    }
  }
  return best
}

function presentFields(group) {
  const present = { entry: false, stopLoss: false, takeProfits: false }
  for (const candidate of group.candidates) {
    if (candidate.fields.entry) present.entry = true
    if (candidate.fields.stopLoss !== null && candidate.fields.stopLoss !== undefined) {
      present.stopLoss = true
    }
    if ((candidate.fields.takeProfits?.length ?? 0) > 0) present.takeProfits = true
  }
  return present
}

function ruleFieldMap(present) {
  const fields = {
    instrument: 'detected_instrument',
    direction: 'detected_direction'
  }
  if (present.entry) fields.entry = 'price_after_entry_label'
  if (present.stopLoss) fields.stopLoss = 'price_after_stop_label'
  if (present.takeProfits) fields.takeProfits = 'prices_after_target_labels'
  return fields
}

function ruleName(group) {
  const instrument = dominantInstrument(group) || 'Signal'
  const present = presentFields(group)
  const parts = ['direction']
  if (present.entry) parts.push('entry')
  if (present.stopLoss) parts.push('SL')
  if (present.takeProfits) parts.push('TP')
  return `${instrument} · ${parts.join(' + ')}`
}

// Sit the threshold a little under the family's average so typical members pass
// while weak outliers fall to the ambiguous queue.
function deriveThreshold(confidenceAvg) {
  return Math.min(1, Math.max(0.5, Number((confidenceAvg - 0.1).toFixed(2))))
}

/**
 * @param {import('./types.js').TemplateGroup} group
 * @returns {import('./types.js').ParserRule}
 */
export function compileRuleFromTemplate(group) {
  const present = presentFields(group)
  return {
    id: `rule_${group.templateKey.replace(/^tpl_/, '')}`,
    name: ruleName(group),
    templateKey: group.templateKey,
    required: ['instrument', 'direction'],
    fields: ruleFieldMap(present),
    rejectIfContains: [...REJECT_PHRASES],
    confidenceThreshold: deriveThreshold(group.confidenceAvg)
  }
}

function toStructuredSignal(candidate, rule) {
  const fields = candidate.fields
  return {
    sourceMessageIds: [candidate.message.id],
    instrument: fields.instrument,
    instrumentRaw: fields.instrumentRaw,
    direction: fields.direction,
    orderType: fields.orderType,
    entry: fields.entry ?? null,
    stopLoss: fields.stopLoss ?? null,
    takeProfits: fields.takeProfits ?? [],
    confidence: candidate.confidence,
    parserRuleId: rule.id,
    intent: candidate.intent
  }
}

function textHasRejectPhrase(rule, candidate) {
  const lower = normalizeMessageText(candidate.message.text).lower
  return rule.rejectIfContains.some((phrase) => lower.includes(phrase))
}

// A message that names an instrument XOR a direction, or carries prices next to a
// trading label without both, is a near miss worth a human glance.
function isPotentialMiss(message) {
  const { clean } = normalizeMessageText(message.text)
  const hasInstrument = detectInstruments(clean).length > 0
  const hasDirection = detectDirections(clean).length > 0
  if (hasInstrument !== hasDirection) return true
  if (!hasInstrument && !hasDirection) {
    return detectPrices(clean).length > 0 && hasTradingLabel(clean)
  }
  return false
}

function routeCandidate(candidate, ruleByKey, buckets) {
  if (NON_SIGNAL_INTENTS.has(candidate.intent)) {
    buckets.rejected.push(candidate)
    return
  }
  const rule = ruleByKey.get(candidate.templateKey)
  if (!rule) {
    buckets.rare.push(candidate)
    return
  }
  if (textHasRejectPhrase(rule, candidate)) {
    buckets.rejected.push(candidate)
    return
  }
  if (
    PARSEABLE_INTENTS.has(candidate.intent) &&
    candidate.confidence >= rule.confidenceThreshold
  ) {
    buckets.parsed.push(toStructuredSignal(candidate, rule))
    return
  }
  buckets.ambiguous.push(candidate)
}

/**
 * @param {import('./types.js').ChatMessage[]} messages
 * @param {import('./types.js').ParserRule[]} rules
 */
export function applyAcceptedRules(messages, rules) {
  const ruleByKey = new Map(rules.map((rule) => [rule.templateKey, rule]))
  const buckets = { parsed: [], ambiguous: [], rejected: [], rare: [], misses: [] }

  for (const message of messages || []) {
    const candidate = attemptExtractSignal(message)
    if (!candidate) {
      if (isPotentialMiss(message)) buckets.misses.push(message)
      continue
    }
    routeCandidate(candidate, ruleByKey, buckets)
  }

  return {
    parsedSignals: buckets.parsed,
    ambiguousCandidates: buckets.ambiguous,
    rejectedCandidates: buckets.rejected,
    rareTemplates: mineTemplateGroups(
      buckets.rare.map((candidate) => candidate.message)
    ),
    potentialMisses: buckets.misses
  }
}
