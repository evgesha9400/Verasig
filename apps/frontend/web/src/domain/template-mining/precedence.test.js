import { describe, expect, it } from 'vitest'
import { matchCandidate, orderRulesByPrecedence } from './rules.js'

/* Precedence turns accepted templates into competing patterns. A candidate is
   claimed by its exact family first; otherwise by the most-specific accepted
   pattern that subsumes it. Ordering is specificity → confidence → coverage,
   so a broad family never steals a specific family's messages. */

const rule = (over) => ({
  templateKey: 'tpl',
  pattern: '<INSTRUMENT>',
  specificity: 1,
  confidenceAvg: 0.8,
  coverage: 1,
  ...over
})

describe('orderRulesByPrecedence', () => {
  it('orders most-specific first, even when a general rule has more coverage', () => {
    const general = rule({
      templateKey: 'g',
      pattern: '<*> <INSTRUMENT>',
      specificity: 0,
      confidenceAvg: 0.95,
      coverage: 100
    })
    const specific = rule({
      templateKey: 's',
      pattern: 'BUY <INSTRUMENT>',
      specificity: 2,
      confidenceAvg: 0.7,
      coverage: 5
    })
    const ordered = orderRulesByPrecedence([general, specific])
    expect(ordered.map((r) => r.templateKey)).toEqual(['s', 'g'])
  })

  it('breaks specificity ties by confidence, then coverage', () => {
    const a = rule({
      templateKey: 'a',
      specificity: 1,
      confidenceAvg: 0.6,
      coverage: 50
    })
    const b = rule({
      templateKey: 'b',
      specificity: 1,
      confidenceAvg: 0.9,
      coverage: 1
    })
    const c = rule({
      templateKey: 'c',
      specificity: 1,
      confidenceAvg: 0.6,
      coverage: 99
    })
    const ordered = orderRulesByPrecedence([a, b, c])
    expect(ordered.map((r) => r.templateKey)).toEqual(['b', 'c', 'a'])
  })

  it('does not mutate the input array', () => {
    const input = [rule({ templateKey: 'x' }), rule({ templateKey: 'y' })]
    orderRulesByPrecedence(input)
    expect(input.map((r) => r.templateKey)).toEqual(['x', 'y'])
  })
})

describe('matchCandidate', () => {
  const exact = rule({
    templateKey: 'tpl_x',
    pattern: 'BUY <INSTRUMENT>',
    specificity: 2
  })
  const general = rule({
    templateKey: 'tpl_g',
    pattern: '<*> <INSTRUMENT>',
    specificity: 0
  })
  const ruleByKey = new Map([
    [exact.templateKey, exact],
    [general.templateKey, general]
  ])
  const ordered = orderRulesByPrecedence([exact, general])

  it('claims a candidate by its exact rule before any fallback', () => {
    const candidate = { templateKey: 'tpl_x', normalizedTemplate: 'BUY <INSTRUMENT>' }
    expect(matchCandidate(candidate, ruleByKey, ordered)).toEqual({
      rule: exact,
      match: 'exact'
    })
  })

  it('recovers a candidate with no exact rule via a subsuming fallback', () => {
    const candidate = {
      templateKey: 'tpl_other',
      normalizedTemplate: 'МОНЕТА <INSTRUMENT>'
    }
    expect(matchCandidate(candidate, ruleByKey, ordered)).toEqual({
      rule: general,
      match: 'fallback'
    })
  })

  it('prefers the most-specific subsuming rule on a fallback', () => {
    const broad = rule({ templateKey: 'tpl_b', pattern: '<*> <*>', specificity: -2 })
    const narrow = rule({ templateKey: 'tpl_a', pattern: 'BUY <*>', specificity: 1 })
    const keys = new Map([
      [broad.templateKey, broad],
      [narrow.templateKey, narrow]
    ])
    const order = orderRulesByPrecedence([broad, narrow])
    const candidate = { templateKey: 'tpl_c', normalizedTemplate: 'BUY <INSTRUMENT>' }
    expect(matchCandidate(candidate, keys, order).rule.templateKey).toBe('tpl_a')
  })

  it('returns null when nothing matches', () => {
    const candidate = { templateKey: 'tpl_none', normalizedTemplate: 'SELL <PRICE>' }
    expect(matchCandidate(candidate, ruleByKey, ordered)).toBeNull()
  })
})
