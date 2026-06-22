import { act, render } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useWorkflowState } from './useWorkflowState.js'

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

  it('sends reviewed feeds to Label only when Review labels is chosen', () => {
    const getWorkflow = renderWorkflow()
    const feed = { ...reviewedFeed, status: 'analyzed' }

    act(() => getWorkflow().upsertFeed(feed))
    act(() => getWorkflow().reviewLabels(feed))

    const workflow = getWorkflow()

    expect(workflow.activeFeedId).toBe(feed.id)
    expect(workflow.screen).toBe('label')
  })
})
