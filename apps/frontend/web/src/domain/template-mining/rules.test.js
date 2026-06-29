import { describe, expect, it } from 'vitest'
import { applyAcceptedRules, compileRuleFromTemplate } from './rules.js'
import { mineTemplateGroups } from './mining.js'

const SIGNALS = [
  { id: 's1', date: '2026-06-01', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355' },
  { id: 's2', date: '2026-06-02', text: 'XAUUSD BUY NOW\nSL 2305\nTP 2330\nTP 2350' },
  { id: 's3', date: '2026-06-03', text: 'XAUUSD BUY NOW\nSL 2300\nTP 2325\nTP 2345' }
]

function signalGroup() {
  return mineTemplateGroups(SIGNALS).find((group) => group.count === SIGNALS.length)
}

describe('compileRuleFromTemplate', () => {
  const rule = compileRuleFromTemplate(signalGroup())

  it('binds the rule to the template key', () => {
    expect(rule.templateKey).toBe(signalGroup().templateKey)
    expect(rule.id).toMatch(/^rule_/)
  })

  it('requires instrument and direction', () => {
    expect(rule.required).toEqual(expect.arrayContaining(['instrument', 'direction']))
  })

  it('maps detected fields to extraction descriptors', () => {
    expect(rule.fields.instrument).toBe('detected_instrument')
    expect(rule.fields.direction).toBe('detected_direction')
    expect(rule.fields.stopLoss).toBe('price_after_stop_label')
    expect(rule.fields.takeProfits).toBe('prices_after_target_labels')
  })

  it('rejects update and result phrasing', () => {
    expect(rule.rejectIfContains).toEqual(
      expect.arrayContaining(['hit tp', 'closed', 'move sl'])
    )
  })

  it('derives a confidence threshold inside (0, 1]', () => {
    expect(rule.confidenceThreshold).toBeGreaterThan(0)
    expect(rule.confidenceThreshold).toBeLessThanOrEqual(1)
  })
})

describe('applyAcceptedRules', () => {
  const rule = compileRuleFromTemplate(signalGroup())
  const messages = [
    ...SIGNALS,
    { id: 'r1', date: '2026-06-02', text: 'XAUUSD BUY hit TP1 ✅' },
    {
      id: 'rare1',
      date: '2026-06-02',
      text: 'GBPJPY short @ 192.50\nSL 193.20\nTP 191.80'
    },
    { id: 'miss1', date: '2026-06-02', text: 'XAUUSD pressing into 2330 resistance' },
    { id: 'noise1', text: 'gm team, link in bio' }
  ]
  const audit = applyAcceptedRules(messages, [rule])

  it('parses signals that match an accepted rule into structured signals', () => {
    expect(audit.parsedSignals).toHaveLength(SIGNALS.length)
    for (const signal of audit.parsedSignals) {
      expect(signal.parserRuleId).toBe(rule.id)
      expect(signal.instrument).toBe('XAUUSD')
      expect(signal.direction).toBe('BUY')
      expect(signal.sourceMessageIds).toHaveLength(1)
    }
  })

  it('rejects update/result candidates', () => {
    expect(audit.rejectedCandidates.some((c) => c.message.id === 'r1')).toBe(true)
  })

  it('surfaces new formats that no accepted rule covers as rare templates', () => {
    const keys = audit.rareTemplates.flatMap((group) =>
      group.candidates.map((c) => c.message.id)
    )
    expect(keys).toContain('rare1')
  })

  it('queues partial-evidence messages as potential misses', () => {
    expect(audit.potentialMisses.some((message) => message.id === 'miss1')).toBe(true)
  })

  it('ignores pure noise entirely', () => {
    const everywhere = [
      ...audit.parsedSignals.flatMap((s) => s.sourceMessageIds),
      ...audit.rejectedCandidates.map((c) => c.message.id),
      ...audit.rareTemplates.flatMap((g) => g.candidates.map((c) => c.message.id)),
      ...audit.potentialMisses.map((m) => m.id)
    ]
    expect(everywhere).not.toContain('noise1')
  })
})
