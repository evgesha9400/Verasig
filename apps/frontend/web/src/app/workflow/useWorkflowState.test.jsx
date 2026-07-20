import { act, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listFeeds } from '../../shared/api/feedsApi.js'
import { getTelegramStatus } from '../../shared/api/telegramApi.js'
import { confirmMining } from '../../shared/api/mineApi.js'
import { useWorkflowState } from './useWorkflowState.js'

vi.mock('../../shared/api/feedsApi.js', () => ({ listFeeds: vi.fn() }))
vi.mock('../../shared/api/telegramApi.js', () => ({ getTelegramStatus: vi.fn() }))
vi.mock('../../shared/api/mineApi.js', () => ({ confirmMining: vi.fn() }))

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

function renderWorkflow(authToken = null) {
  let workflow

  function Harness() {
    workflow = useWorkflowState(authToken)
    return null
  }

  render(<Harness />)
  return () => workflow
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
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
    vi.clearAllMocks()
    getTelegramStatus.mockResolvedValue({ connected: true })
    listFeeds.mockResolvedValue({ feeds: [] })
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

  it('uses the exact authenticated feed state returned by refresh', async () => {
    const serverFeed = {
      ...reviewedFeed,
      status: 'backfilled',
      hasRisk: false,
      fetched: 12,
      lastDate: 'Jun 3, 2026'
    }
    listFeeds.mockResolvedValueOnce({ feeds: [serverFeed] })
    const getWorkflow = renderWorkflow('jwt-token')

    await waitFor(() => expect(getWorkflow().feeds).toEqual([serverFeed]))
    expect(getWorkflow().feeds[0].status).toBe('backfilled')
    expect(getWorkflow().feeds[0].hasRisk).toBe(false)
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

  it('keeps Verify and the feed unchanged while confirmation is pending', async () => {
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }
    const confirmation = deferred()
    listFeeds.mockResolvedValueOnce({ feeds: [feed] })
    confirmMining.mockReturnValueOnce(confirmation.promise)
    const getWorkflow = renderWorkflow('jwt-token')
    await waitFor(() => expect(getWorkflow().feeds).toEqual([feed]))
    act(() => {
      getWorkflow().setActiveFeedId(feed.id)
      getWorkflow().setScreen('verify')
    })

    let command
    act(() => {
      command = getWorkflow().confirmVerification({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_accept'],
        destination: 'feeds'
      })
    })

    expect(getWorkflow().screen).toBe('verify')
    expect(getWorkflow().feeds).toEqual([feed])

    confirmation.reject(new Error('cancel pending test'))
    await expect(command).rejects.toThrow('cancel pending test')
  })

  it('rejects confirmation without changing status or navigation and permits retry', async () => {
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }
    listFeeds.mockResolvedValueOnce({ feeds: [feed] })
    confirmMining
      .mockRejectedValueOnce(new Error('Confirmation unavailable.'))
      .mockResolvedValueOnce({ feedStatus: 'verified' })
    listFeeds.mockResolvedValueOnce({
      feeds: [{ ...feed, status: 'verified', hasRisk: false }]
    })
    const getWorkflow = renderWorkflow('jwt-token')
    await waitFor(() => expect(getWorkflow().feeds).toEqual([feed]))
    act(() => {
      getWorkflow().setActiveFeedId(feed.id)
      getWorkflow().setScreen('verify')
    })

    await expect(
      getWorkflow().confirmVerification({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_accept'],
        destination: 'feeds'
      })
    ).rejects.toThrow('Confirmation unavailable.')
    expect(getWorkflow().screen).toBe('verify')
    expect(getWorkflow().feeds).toEqual([feed])

    await act(async () => {
      await getWorkflow().confirmVerification({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_accept'],
        destination: 'feeds'
      })
    })
    expect(confirmMining).toHaveBeenCalledTimes(2)
    expect(getWorkflow().screen).toBe('feeds')
  })

  it('awaits server verification and exact refresh before navigation and toast', async () => {
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }
    const verifiedServerFeed = {
      ...feed,
      status: 'verified',
      hasRisk: false,
      fetched: 19
    }
    const order = []
    listFeeds
      .mockResolvedValueOnce({ feeds: [feed] })
      .mockImplementationOnce(async () => {
        order.push('refresh')
        return { feeds: [verifiedServerFeed] }
      })
    confirmMining.mockImplementationOnce(async () => {
      order.push('confirm')
      return { feedStatus: 'verified' }
    })
    const getWorkflow = renderWorkflow('jwt-token')
    await waitFor(() => expect(getWorkflow().feeds).toEqual([feed]))
    act(() => {
      getWorkflow().setActiveFeedId(feed.id)
      getWorkflow().setScreen('verify')
    })

    await act(async () => {
      await getWorkflow().confirmVerification({
        reviewId: 'review-1',
        acceptedTemplateKeys: ['tpl_accept'],
        destination: 'exchange'
      })
    })

    expect(order).toEqual(['confirm', 'refresh'])
    expect(confirmMining).toHaveBeenCalledWith('jwt-token', feed.id, 'review-1', [
      'tpl_accept'
    ])
    expect(getWorkflow().feeds).toEqual([verifiedServerFeed])
    expect(getWorkflow().feeds[0].hasRisk).toBe(false)
    expect(getWorkflow().screen).toBe('exchange')
    expect(getWorkflow().toast.title).toBe('Source verified')
  })

  it('does not accept a confirmation whose refreshed server feed is backfilled', async () => {
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }
    listFeeds
      .mockResolvedValueOnce({ feeds: [feed] })
      .mockResolvedValueOnce({ feeds: [{ ...feed, fetched: 21 }] })
    confirmMining.mockResolvedValueOnce({ feedStatus: 'verified' })
    const getWorkflow = renderWorkflow('jwt-token')
    await waitFor(() => expect(getWorkflow().feeds).toEqual([feed]))
    act(() => {
      getWorkflow().setActiveFeedId(feed.id)
      getWorkflow().setScreen('verify')
    })

    let commandError
    await act(async () => {
      try {
        await getWorkflow().confirmVerification({
          reviewId: 'review-1',
          acceptedTemplateKeys: ['tpl_accept'],
          destination: 'feeds'
        })
      } catch (error) {
        commandError = error
      }
    })

    expect(commandError?.message).toMatch(/server did not confirm/i)
    expect(getWorkflow().screen).toBe('verify')
    expect(getWorkflow().feeds[0]).toEqual({ ...feed, fetched: 21 })
  })

  it('preserves explicit local demo confirmation behavior', async () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'backfilled', hasRisk: false }
    act(() => {
      getWorkflow().upsertFeed(feed)
      getWorkflow().setActiveFeedId(feed.id)
      getWorkflow().setScreen('verify')
    })

    await act(async () => {
      await getWorkflow().confirmVerification({ destination: 'feeds' })
    })

    expect(getWorkflow().feeds.find((candidate) => candidate.id === feed.id)).toEqual(
      expect.objectContaining({ status: 'verified', hasRisk: true })
    )
    expect(getWorkflow().screen).toBe('feeds')
    expect(confirmMining).not.toHaveBeenCalled()
  })
})
