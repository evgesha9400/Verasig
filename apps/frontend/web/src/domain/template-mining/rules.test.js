import { describe, expect, it } from 'vitest'
import { applyAcceptedRules, compileRuleFromTemplate } from './rules.js'
import { mineTemplateGroups } from './mining.js'
import { SAMPLE_MESSAGES } from './sampleMessages.js'

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

  it('does not surface an instrument-only result post as a potential miss', () => {
    const result = applyAcceptedRules([{ id: 'o1', text: 'XAUUSD hit TP1' }], [rule])
    expect(result.potentialMisses.some((m) => m.id === 'o1')).toBe(false)
  })

  it('does not reject a genuine signal that merely contains a reject substring', () => {
    const family = [
      { id: 'c1', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nManage closely' },
      { id: 'c2', text: 'XAUUSD BUY NOW\nSL 2305\nTP 2330\nManage closely' },
      { id: 'c3', text: 'XAUUSD BUY NOW\nSL 2300\nTP 2325\nManage closely' }
    ]
    const familyRule = compileRuleFromTemplate(
      mineTemplateGroups(family).find((group) => group.count === family.length)
    )
    const result = applyAcceptedRules(family, [familyRule])
    expect(result.parsedSignals).toHaveLength(family.length)
    expect(result.rejectedCandidates).toHaveLength(0)
  })
})

describe('no-regression: accept-all keeps exact routing', () => {
  // When every mined family is accepted, each candidate's exact templateKey is
  // present, so precedence/fallback can never fire — behaviour equals the old
  // exact-key router. This golden test gates the precedence wiring.
  it('routes every candidate by its exact family — no fallback, nothing rare', () => {
    const rules = mineTemplateGroups(SAMPLE_MESSAGES).map((group) =>
      compileRuleFromTemplate(group)
    )
    const audit = applyAcceptedRules(SAMPLE_MESSAGES, rules)
    expect(audit.parsedSignals.length).toBeGreaterThan(0)
    expect(audit.parsedSignals.every((signal) => signal.match === 'exact')).toBe(true)
    expect(audit.rareTemplates).toHaveLength(0)
  })
})

describe('fallback recovery', () => {
  // A general family whose leading word varies (so it normalizes to a <*> slot).
  const general = [
    { id: 'g1', date: '2026-06-01', text: 'Alpha SOLUSDT BUY\nSL 100\nTP 120' },
    { id: 'g2', date: '2026-06-02', text: 'Beta SOLUSDT BUY\nSL 101\nTP 121' },
    { id: 'g3', date: '2026-06-03', text: 'Gamma SOLUSDT BUY\nSL 102\nTP 122' }
  ]
  const generalRule = compileRuleFromTemplate(
    mineTemplateGroups(general).find((group) => group.count === general.length)
  )

  it('recovers a near-miss message via a subsuming general rule, tagged fallback', () => {
    // "Монета" is a structural word, so this message exactly matches NO accepted
    // family — but the general <*> family subsumes it and should claim it.
    const specific = { id: 'spec1', text: 'Монета SOLUSDT BUY\nSL 100\nTP 120' }
    const audit = applyAcceptedRules([specific], [generalRule])
    const parsed = audit.parsedSignals.find((s) => s.sourceMessageIds.includes('spec1'))
    expect(parsed).toBeTruthy()
    expect(parsed.match).toBe('fallback')
    expect(parsed.parserRuleId).toBe(generalRule.id)
  })

  it('tags an exact-family match as exact, not fallback', () => {
    const audit = applyAcceptedRules(general, [generalRule])
    expect(audit.parsedSignals).toHaveLength(general.length)
    for (const signal of audit.parsedSignals) expect(signal.match).toBe('exact')
  })
})

describe('overlay integration', () => {
  it('lowers a template threshold from the overlay', () => {
    const group = {
      templateKey: 'tpl_demo',
      confidenceAvg: 0.9,
      candidates: [
        { fields: { orderType: 'limit', entry: {}, stopLoss: 1, takeProfits: [1] } }
      ]
    }
    const base = compileRuleFromTemplate(group)
    const tuned = compileRuleFromTemplate(group, {
      templateThresholds: { tpl_demo: 0.42 }
    })
    expect(tuned.confidenceThreshold).toBe(0.42)
    expect(tuned.confidenceThreshold).not.toBe(base.confidenceThreshold)
  })

  it('appends overlay reject phrases to a compiled rule', () => {
    const group = {
      templateKey: 'tpl_demo',
      confidenceAvg: 0.9,
      candidates: [
        { fields: { orderType: 'limit', entry: {}, stopLoss: 1, takeProfits: [1] } }
      ]
    }
    const rule = compileRuleFromTemplate(group, { rejectPhrases: ['giveaway'] })
    expect(rule.rejectIfContains).toContain('giveaway')
  })
})
