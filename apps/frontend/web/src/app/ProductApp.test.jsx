import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { getParserOverlay, putParserOverlay } from '../shared/api/pipelineApi.js'
import { deletionRescanToast, useParserOverlay } from './ProductApp.jsx'

vi.mock('../shared/api/pipelineApi.js', () => ({
  getParserOverlay: vi.fn(),
  putParserOverlay: vi.fn()
}))

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

describe('useParserOverlay', () => {
  it('ignores a late boot read that resolves after an overlay was saved', async () => {
    let resolveBoot
    getParserOverlay
      .mockImplementationOnce(() => new Promise((resolve) => (resolveBoot = resolve)))
      .mockResolvedValueOnce({ overlay: {} })
    putParserOverlay.mockResolvedValueOnce({ overlay: { rule: 'saved' } })

    const { result } = renderHook(() => useParserOverlay('token', vi.fn()))
    await act(() => result.current.saveOverlay({ rule: 'saved' }))
    expect(result.current.overlay).toEqual({ rule: 'saved' })

    await act(async () => resolveBoot({ overlay: { rule: 'stale' } }))
    await waitFor(() => expect(result.current.overlay).toEqual({ rule: 'saved' }))
  })
})
