/* Verasig — Template Mining: grouping candidates into reviewable families.
   Every message is parsed; the ones that clear the bar are bucketed by templateKey.
   Each family carries the stats a reviewer needs — count, average confidence,
   intent mix, date range, examples — plus a suggested action so the obviously
   good and obviously bad families need no thought. */

import { attemptExtractSignal } from './extract.js'

const ACCEPT_CONFIDENCE = 0.6
const ACCEPT_SIGNAL_SHARE = 0.6
const REJECT_NONSIGNAL_SHARE = 0.5
const MAX_EXAMPLES = 5

function emptyIntentDistribution() {
  return { new_signal: 0, update: 0, result: 0, commentary: 0, unknown: 0 }
}

function bucketByTemplate(candidates) {
  const buckets = new Map()
  for (const candidate of candidates) {
    const existing = buckets.get(candidate.templateKey)
    if (existing) existing.push(candidate)
    else buckets.set(candidate.templateKey, [candidate])
  }
  return buckets
}

function averageConfidence(candidates) {
  const total = candidates.reduce((sum, candidate) => sum + candidate.confidence, 0)
  return total / candidates.length
}

function intentDistribution(candidates) {
  const distribution = emptyIntentDistribution()
  for (const candidate of candidates) distribution[candidate.intent] += 1
  return distribution
}

function dateRange(candidates) {
  const dates = candidates
    .map((candidate) => candidate.message.date)
    .filter(Boolean)
    .sort()
  if (dates.length === 0) return undefined
  return { from: dates[0], to: dates[dates.length - 1] }
}

function topExamples(candidates) {
  return [...candidates]
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, MAX_EXAMPLES)
}

function suggestAction(distribution, count, confidenceAvg) {
  const signalShare = distribution.new_signal / count
  const nonSignalShare =
    (distribution.update + distribution.result + distribution.commentary) / count
  if (signalShare >= ACCEPT_SIGNAL_SHARE && confidenceAvg >= ACCEPT_CONFIDENCE) {
    return 'accept'
  }
  if (nonSignalShare > REJECT_NONSIGNAL_SHARE) return 'reject'
  return 'review'
}

const ACTION_RANK = { review: 0, accept: 1, reject: 2 }

function toGroup(templateKey, candidates) {
  const count = candidates.length
  const confidenceAvg = averageConfidence(candidates)
  const distribution = intentDistribution(candidates)
  return {
    id: templateKey,
    templateKey,
    normalizedTemplate: candidates[0].normalizedTemplate,
    candidates,
    examples: topExamples(candidates),
    count,
    dateRange: dateRange(candidates),
    confidenceAvg,
    intentDistribution: distribution,
    status: 'unreviewed',
    suggestedAction: suggestAction(distribution, count, confidenceAvg)
  }
}

// Bigger families first; ties broken by confidence, then by surfacing review
// families ahead of already-decided ones.
function sortGroups(groups) {
  return groups.sort(
    (a, b) =>
      b.count - a.count ||
      b.confidenceAvg - a.confidenceAvg ||
      ACTION_RANK[a.suggestedAction] - ACTION_RANK[b.suggestedAction]
  )
}

/**
 * @param {import('./types.js').ChatMessage[]} messages
 * @returns {import('./types.js').TemplateGroup[]}
 */
export function mineTemplateGroups(messages) {
  const candidates = (messages || []).map(attemptExtractSignal).filter(Boolean)
  const buckets = bucketByTemplate(candidates)
  const groups = [...buckets.entries()].map(([key, list]) => toGroup(key, list))
  return sortGroups(groups)
}
