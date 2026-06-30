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
import { attemptExtractSignal, classifyMessageIntent } from './extract.js'
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

// A family's order type spans every instrument in it; describe the FORMAT, not a
// sample symbol, so a multi-instrument family is not mislabelled as one coin.
function dominantOrderType(group) {
  const counts = new Map()
  for (const candidate of group.candidates) {
    const type = candidate.fields.orderType || 'unknown'
    counts.set(type, (counts.get(type) || 0) + 1)
  }
  let best = 'market'
  let bestCount = -1
  for (const [type, count] of counts) {
    if (count > bestCount) {
      best = type
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

const ORDER_TYPE_LABEL = {
  market: 'Market',
  limit: 'Limit',
  range: 'Range',
  unknown: 'Signal'
}

export function formatLabel(group) {
  const present = presentFields(group)
  const parts = ['direction']
  if (present.entry) parts.push('entry')
  if (present.stopLoss) parts.push('SL')
  if (present.takeProfits) parts.push('TP')
  return `${ORDER_TYPE_LABEL[dominantOrderType(group)]} signal · ${parts.join(' + ')}`
}

// Sit the threshold a little under the family's average so typical members pass
// while weak outliers fall to the ambiguous queue.
function deriveThreshold(confidenceAvg) {
  return Math.min(1, Math.max(0.5, Number((confidenceAvg - 0.1).toFixed(2))))
}

/**
 * @param {import('./types.js').TemplateGroup} group
 * @param {Object} overlay
 * @returns {import('./types.js').ParserRule}
 */
export function compileRuleFromTemplate(group, overlay = {}) {
  const present = presentFields(group)
  const overrideThreshold = overlay?.templateThresholds?.[group.templateKey]
  return {
    id: `rule_${group.templateKey.replace(/^tpl_/, '')}`,
    name: formatLabel(group),
    templateKey: group.templateKey,
    required: ['instrument', 'direction'],
    fields: ruleFieldMap(present),
    rejectIfContains: [...REJECT_PHRASES, ...(overlay?.rejectPhrases ?? [])],
    confidenceThreshold:
      typeof overrideThreshold === 'number'
        ? overrideThreshold
        : deriveThreshold(group.confidenceAvg)
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

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Match reject phrases on word boundaries (spaces tolerate any whitespace), so
// "closely"/"pipsqueak" do not trip the bare "close"/"pips" phrases the way a
// raw substring check would.
function phraseMatches(phrase, lower) {
  const body = escapeRegExp(phrase).replace(/\s+/g, '\\s+')
  return new RegExp(`\\b${body}\\b`, 'i').test(lower)
}

function textHasRejectPhrase(rule, candidate) {
  const lower = normalizeMessageText(candidate.message.text).lower
  return rule.rejectIfContains.some((phrase) => phraseMatches(phrase, lower))
}

// A message that names an instrument XOR a direction, or carries prices next to a
// trading label without both, is a near miss worth a human glance.
function isPotentialMiss(message, overlay) {
  const { clean } = normalizeMessageText(message.text)
  const hasInstrument = detectInstruments(clean, overlay).length > 0
  const hasDirection = detectDirections(clean, overlay).length > 0
  if (hasInstrument !== hasDirection) return true
  if (!hasInstrument && !hasDirection) {
    return detectPrices(clean).length > 0 && hasTradingLabel(clean)
  }
  return false
}

// Candidates are always new signals now; match them to an accepted rule.
function routeCandidate(candidate, ruleByKey, buckets) {
  const rule = ruleByKey.get(candidate.templateKey)
  if (!rule) {
    buckets.rare.push(candidate)
    return
  }
  if (textHasRejectPhrase(rule, candidate)) {
    buckets.rejected.push({ message: candidate.message, intent: candidate.intent })
    return
  }
  if (candidate.confidence >= rule.confidenceThreshold) {
    buckets.parsed.push(toStructuredSignal(candidate, rule))
    return
  }
  buckets.ambiguous.push(candidate)
}

// A non-candidate message that reads as an update/result is bucketed as rejected
// (without becoming a template family); a partial-evidence one is a potential miss.
function routeNonCandidate(message, buckets, overlay) {
  const intent = classifyMessageIntent(message, overlay)
  if (NON_SIGNAL_INTENTS.has(intent)) {
    buckets.rejected.push({ message, intent })
    return
  }
  if (isPotentialMiss(message, overlay)) buckets.misses.push(message)
}

/**
 * @param {import('./types.js').ChatMessage[]} messages
 * @param {import('./types.js').ParserRule[]} rules
 * @param {Object} overlay
 */
export function applyAcceptedRules(messages, rules, overlay = {}) {
  const ruleByKey = new Map(rules.map((rule) => [rule.templateKey, rule]))
  const buckets = { parsed: [], ambiguous: [], rejected: [], rare: [], misses: [] }

  for (const message of messages || []) {
    const candidate = attemptExtractSignal(message, overlay)
    if (!candidate) {
      routeNonCandidate(message, buckets, overlay)
      continue
    }
    routeCandidate(candidate, ruleByKey, buckets)
  }

  return {
    parsedSignals: buckets.parsed,
    ambiguousCandidates: buckets.ambiguous,
    rejectedCandidates: buckets.rejected,
    rareTemplates: mineTemplateGroups(
      buckets.rare.map((candidate) => candidate.message),
      overlay
    ),
    potentialMisses: buckets.misses
  }
}
