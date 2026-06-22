import { describe, expect, it } from 'vitest'
import { deletionRescanToast } from './ProductApp.jsx'

const feed = { name: 'Pilot Signals' }

describe('deletionRescanToast', () => {
  it('uses rejected tone for new signal deletions', () => {
    expect(
      deletionRescanToast(feed, {
        newDeletedSignalCount: 1,
        newDeletedNonSignalCount: 0,
        newSuspectedGapCount: 0
      })
    ).toEqual({
      tone: 'rejected',
      title: 'Signal deletion confirmed',
      msg: 'Pilot Signals has 1 deleted signal message.'
    })
  })

  it('uses pending tone for warning-only deletions and gaps', () => {
    expect(
      deletionRescanToast(feed, {
        newDeletedSignalCount: 0,
        newDeletedNonSignalCount: 2,
        newSuspectedGapCount: 1
      })
    ).toEqual({
      tone: 'pending',
      title: 'Deleted messages found',
      msg: 'Pilot Signals has 3 newly detected deleted or missing messages that are not signals.'
    })
  })

  it('uses verified tone when no new evidence appears', () => {
    expect(
      deletionRescanToast(feed, {
        newDeletedSignalCount: 0,
        newDeletedNonSignalCount: 0,
        newSuspectedGapCount: 0
      })
    ).toEqual({
      tone: 'verified',
      title: 'No deleted messages found',
      msg: 'Pilot Signals has no newly detected deleted messages.'
    })
  })
})
