import { act, render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mergeReviewedFeedState, useWorkflowState } from './useWorkflowState.js'

const reviewedFeed = {
  id: 'reviewed-feed',
  name: 'Reviewed Signals',
  tag: '@reviewed',
  initials: 'RS',
  tint: '#5197ff',
  source: 'telegram',
  status: 'verified',
  fetched: 3,
  lastDate: 'Jun 1, 2026',
  score: 91,
  winRate: 62,
  pnl: 14,
  hasRisk: true,
  historyGaps: false,
  signalDeletion: false,
  deletedCount: 0
}

function renderWorkflow() {
  let workflow

  function Harness() {
    workflow = useWorkflowState(null)
    return null
  }

  render(<Harness />)
  return () => workflow
}

function createTestStorage() {
  const entries = new Map()

  return {
    getItem: (key) => {
      const storageKey = String(key)
      return entries.has(storageKey) ? entries.get(storageKey) : null
    },
    setItem: (key, value) => {
      entries.set(String(key), String(value))
    },
    removeItem: (key) => {
      entries.delete(String(key))
    },
    clear: () => {
      entries.clear()
    }
  }
}

function installTestStorage() {
  const storage = createTestStorage()
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true
  })
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    configurable: true
  })
}

describe('useWorkflowState', () => {
  beforeEach(() => {
    installTestStorage()
    localStorage.clear()
  })

  it('clears the previous toast timer so a rapid second toast is not cut short', () => {
    vi.useFakeTimers()
    try {
      const getWorkflow = renderWorkflow()

      act(() => getWorkflow().fireToast('info', 'A', 'first'))
      act(() => vi.advanceTimersByTime(2000))
      act(() => getWorkflow().fireToast('info', 'B', 'second'))

      // The first toast's original 4200ms deadline passes; its stale timer must
      // not clear the second toast that only just appeared.
      act(() => vi.advanceTimersByTime(2300))
      expect(getWorkflow().toast?.title).toBe('B')

      // The second toast clears on its own deadline.
      act(() => vi.advanceTimersByTime(2000))
      expect(getWorkflow().toast).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })

  it.each(['verified', 'analyzed'])(
    'keeps %s feeds verified after fetching new messages',
    (status) => {
      const getWorkflow = renderWorkflow()
      const feed = { ...reviewedFeed, status }

      act(() => getWorkflow().upsertFeed(feed))
      act(() => getWorkflow().fetchNewMessages(feed))
      act(() =>
        getWorkflow().onBackfillComplete({
          fetched: 5,
          lastDate: 'Jun 2, 2026',
          status: 'succeeded'
        })
      )

      const workflow = getWorkflow()
      const saved = workflow.feeds.find((candidate) => candidate.id === feed.id)

      expect(saved.status).toBe(status)
      expect(saved.fetched).toBe(5)
      expect(saved.lastDate).toBe('Jun 2, 2026')
      expect(workflow.screen).toBe('feeds')
      expect(workflow.toast.title).toBe('Messages fetched')
      expect(workflow.toast.msg).toContain('Verification is still saved')
    }
  )

  it('keeps reviewed feeds verified when refresh fails', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'verified' }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().fetchNewMessages(feed))
    act(() =>
      getWorkflow().onBackfillError({
        fetched: 3,
        lastDate: 'Jun 1, 2026',
        status: 'failed',
        message: 'Telegram unavailable.'
      })
    )

    const workflow = getWorkflow()
    const saved = workflow.feeds.find((candidate) => candidate.id === feed.id)

    expect(saved.status).toBe('verified')
    expect(workflow.screen).toBe('feeds')
    expect(workflow.toast.title).toBe('Fetch failed')
    expect(workflow.toast.msg).toContain('Verification is still saved')
  })

  it('keeps reviewed feeds verified when refresh is cancelled', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'verified' }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().fetchNewMessages(feed))
    act(() => getWorkflow().onBackfillCancel(3, 'Jun 1, 2026'))

    const workflow = getWorkflow()
    const saved = workflow.feeds.find((candidate) => candidate.id === feed.id)

    expect(saved.status).toBe('verified')
    expect(workflow.screen).toBe('feeds')
    expect(workflow.toast.title).toBe('Fetch cancelled')
    expect(workflow.toast.msg).toContain('Verification is still saved')
  })

  it('reopens reviewed feeds in Mining when Review templates is chosen', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'analyzed' }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().reopenMining(feed))

    const workflow = getWorkflow()

    expect(workflow.activeFeedId).toBe(feed.id)
    expect(workflow.screen).toBe('mine')
  })

  it('confirms stepping back to Mine only from a later pipeline step', () => {
    const getWorkflow = renderWorkflow()

    // From a step positioned after Mine (Exchange), stepping back to Mine
    // opens the confirmation dialog rather than jumping straight back.
    act(() => getWorkflow().setScreen('exchange'))
    act(() => getWorkflow().requestStepBack('mine'))

    let workflow = getWorkflow()
    expect(workflow.backTarget).toBe('mine')
    expect(workflow.screen).toBe('exchange')

    act(() => getWorkflow().confirmStepBack())
    workflow = getWorkflow()
    expect(workflow.backTarget).toBe(null)
    expect(workflow.screen).toBe('mine')
    expect(workflow.toast.title).toBe('Back to Mining')

    // From a step at or before Mine, stepping back navigates with no dialog.
    act(() => getWorkflow().setScreen('mine'))
    act(() => getWorkflow().requestStepBack('backfill'))

    workflow = getWorkflow()
    expect(workflow.backTarget).toBe(null)
    expect(workflow.screen).toBe('backfill')
  })

  it('keeps reviewed local status when a refreshed feed briefly returns backfilled', () => {
    const merged = mergeReviewedFeedState(
      [{ ...reviewedFeed, status: 'verified', hasRisk: true }],
      [
        {
          ...reviewedFeed,
          status: 'backfilled',
          hasRisk: false,
          fetched: 12,
          lastDate: 'Jun 3, 2026'
        }
      ]
    )

    expect(merged[0].status).toBe('verified')
    expect(merged[0].hasRisk).toBe(true)
    expect(merged[0].fetched).toBe(12)
    expect(merged[0].lastDate).toBe('Jun 3, 2026')
  })

  it('keeps rules-backed backfilled feeds reviewable after source refresh', () => {
    const merged = mergeReviewedFeedState(
      [{ ...reviewedFeed, status: 'backfilled', hasRisk: true }],
      [
        {
          ...reviewedFeed,
          status: 'backfilled',
          hasRisk: false,
          fetched: 12,
          lastDate: 'Jun 3, 2026'
        }
      ]
    )

    expect(merged[0].status).toBe('backfilled')
    expect(merged[0].hasRisk).toBe(true)
    expect(merged[0].fetched).toBe(12)
    expect(merged[0].lastDate).toBe('Jun 3, 2026')
  })

  it('opens backfilled feeds at Mine regardless of prior rules', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: true }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().resumeFeed(feed))

    const workflow = getWorkflow()

    expect(workflow.activeFeedId).toBe(feed.id)
    expect(workflow.screen).toBe('mine')
  })

  it('keeps rules-backed backfilled feeds out of Label after fetching new messages', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: true }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().fetchNewMessages(feed))
    act(() =>
      getWorkflow().onBackfillComplete({
        fetched: 12,
        lastDate: 'Jun 3, 2026',
        status: 'succeeded'
      })
    )

    const workflow = getWorkflow()
    const saved = workflow.feeds.find((candidate) => candidate.id === feed.id)

    expect(saved.status).toBe('backfilled')
    expect(saved.hasRisk).toBe(true)
    expect(workflow.screen).toBe('feeds')
  })

  it('keeps Route & backtest feeds verified before later fetching new messages', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().setActiveFeedId(feed.id))
    act(() => getWorkflow().routeAfterVerify())

    const verifiedFeed = getWorkflow().feeds.find(
      (candidate) => candidate.id === feed.id
    )
    expect(verifiedFeed.status).toBe('verified')
    expect(verifiedFeed.hasRisk).toBe(true)
    expect(getWorkflow().screen).toBe('exchange')

    act(() => getWorkflow().fetchNewMessages(verifiedFeed))
    act(() =>
      getWorkflow().onBackfillComplete({
        fetched: 12,
        lastDate: 'Jun 3, 2026',
        status: 'succeeded'
      })
    )

    const refreshedFeed = getWorkflow().feeds.find(
      (candidate) => candidate.id === feed.id
    )
    act(() => getWorkflow().resumeFeed(refreshedFeed))

    expect(refreshedFeed.status).toBe('verified')
    expect(getWorkflow().screen).toBe('verify')
  })
})
