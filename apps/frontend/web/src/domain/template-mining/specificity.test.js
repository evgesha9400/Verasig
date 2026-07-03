import { describe, expect, it } from 'vitest'
import { templateSpecificity } from './specificity.js'

/* Specificity ranks how much literal structure a normalized template carries.
   It breaks precedence ties so the most-specific accepted family wins, and
   guarantees a generalized (wildcarded) pattern never outranks a literal one. */

describe('templateSpecificity', () => {
  it('scores a literal+placeholder template above a sparser one', () => {
    expect(templateSpecificity('МОНЕТА <INSTRUMENT> <SIDE>')).toBeGreaterThan(
      templateSpecificity('<INSTRUMENT> <SIDE>')
    )
  })

  it('penalises a <*> wildcard below a literal structural word', () => {
    expect(templateSpecificity('МОНЕТА <INSTRUMENT>')).toBeGreaterThan(
      templateSpecificity('<*> <INSTRUMENT>')
    )
  })

  it('counts value placeholders as structure', () => {
    expect(templateSpecificity('<INSTRUMENT> <PRICE> <SIDE>')).toBeGreaterThan(
      templateSpecificity('<INSTRUMENT>')
    )
  })

  it('sums structure across multiple lines', () => {
    expect(templateSpecificity('BUY <INSTRUMENT>\nSL <PRICE>')).toBeGreaterThan(
      templateSpecificity('BUY <INSTRUMENT>')
    )
  })

  it('returns 0 for an empty or missing template', () => {
    expect(templateSpecificity('')).toBe(0)
    expect(templateSpecificity(undefined)).toBe(0)
  })
})
