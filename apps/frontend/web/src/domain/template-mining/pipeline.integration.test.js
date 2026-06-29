import { describe, expect, it } from 'vitest'
import {
  SAMPLE_MESSAGES,
  FEED_MESSAGES,
  mineTemplateGroups,
  compileRuleFromTemplate,
  applyAcceptedRules
} from './index.js'

describe('template mining — end to end over the sample dataset', () => {
  const groups = mineTemplateGroups(SAMPLE_MESSAGES)

  it('ships at least forty representative messages', () => {
    expect(SAMPLE_MESSAGES.length).toBeGreaterThanOrEqual(40)
  })

  it('discovers several distinct template families', () => {
    expect(groups.length).toBeGreaterThanOrEqual(6)
  })

  it('finds families it suggests accepting and families it suggests rejecting', () => {
    const actions = new Set(groups.map((group) => group.suggestedAction))
    expect(actions.has('accept')).toBe(true)
    expect(actions.has('reject')).toBe(true)
  })

  it('parses accepted families over the full history with no noise leaking in', () => {
    const accepted = groups.filter((group) => group.suggestedAction === 'accept')
    const rules = accepted.map(compileRuleFromTemplate)
    const audit = applyAcceptedRules(SAMPLE_MESSAGES, rules)

    expect(audit.parsedSignals.length).toBeGreaterThan(0)
    // Every parsed signal carries the minimum required fields.
    for (const signal of audit.parsedSignals) {
      expect(signal.instrument).toBeTruthy()
      expect(['BUY', 'SELL']).toContain(signal.direction)
      expect(signal.parserRuleId).toMatch(/^rule_/)
    }
    // Update/result messages are caught, not parsed as new signals.
    expect(audit.rejectedCandidates.length).toBeGreaterThan(0)
  })
})

describe('template mining — runs against the connected feed history', () => {
  it('extracts candidates from the demo feed messages', () => {
    const groups = mineTemplateGroups(FEED_MESSAGES)
    const candidates = groups.reduce((sum, group) => sum + group.count, 0)
    expect(candidates).toBeGreaterThan(0)
  })
})
