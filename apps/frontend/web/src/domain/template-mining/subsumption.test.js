import { describe, expect, it } from 'vitest'
import { patternSubsumes } from './subsumption.js'

/* Subsumption: does an accepted rule's pattern match a message skeleton, possibly
   generalizing? A <*> slot absorbs one token; a general placeholder matches a more
   specific one it subsumes. Matching is one-directional — a specific pattern never
   matches a more-general message. */

describe('patternSubsumes', () => {
  it('matches an identical skeleton', () => {
    expect(patternSubsumes('BUY <INSTRUMENT>', 'BUY <INSTRUMENT>')).toBe(true)
  })

  it('absorbs any single word where the pattern has <*>', () => {
    expect(patternSubsumes('<*> <INSTRUMENT>', 'МОНЕТА <INSTRUMENT>')).toBe(true)
  })

  it('does not match when a literal word differs', () => {
    expect(patternSubsumes('BUY <INSTRUMENT>', 'SELL <INSTRUMENT>')).toBe(false)
  })

  it('generalizes <PRICE_LIST> over a single <PRICE>', () => {
    expect(patternSubsumes('<INSTRUMENT> <PRICE_LIST>', '<INSTRUMENT> <PRICE>')).toBe(
      true
    )
  })

  it('generalizes <SIDE> over <SIDE_EMOJI>', () => {
    expect(patternSubsumes('<SIDE> <INSTRUMENT>', '<SIDE_EMOJI> <INSTRUMENT>')).toBe(
      true
    )
  })

  it('is one-directional: a specific pattern does not match a general message', () => {
    expect(patternSubsumes('<INSTRUMENT> <PRICE>', '<INSTRUMENT> <PRICE_LIST>')).toBe(
      false
    )
  })

  it('keeps <RANGE> and <PRICE> distinct', () => {
    expect(patternSubsumes('<INSTRUMENT> <RANGE>', '<INSTRUMENT> <PRICE>')).toBe(false)
  })

  it('requires the same number of lines', () => {
    expect(patternSubsumes('BUY <INSTRUMENT>', 'BUY <INSTRUMENT>\n<PRICE>')).toBe(false)
  })

  it('requires the same token count on a line', () => {
    expect(patternSubsumes('<INSTRUMENT>', '<INSTRUMENT> <PRICE>')).toBe(false)
  })

  it('matches a multi-line skeleton where every line subsumes', () => {
    expect(
      patternSubsumes(
        '<*> <INSTRUMENT>\nСТОП <PRICE>\nЦЕЛИ <PRICE_LIST>',
        'МОНЕТА <INSTRUMENT>\nСТОП <PRICE>\nЦЕЛИ <PRICE>'
      )
    ).toBe(true)
  })
})
