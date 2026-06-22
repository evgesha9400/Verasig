import { useCallback, useEffect, useRef, useState } from 'react'
import { listFeeds } from '../../shared/api/feedsApi.js'
import { getTelegramStatus } from '../../shared/api/telegramApi.js'
import { PIPELINE_STEPS } from '../../domain/workflow/pipelineSteps.js'
import { FEEDS } from '../../domain/demo-data/seed.js'

const LS_KEY = 'vrs-proto-state-2'

const PIPELINE_SCREEN_BY_SCREEN = {
  backfill: 'backfill',
  label: 'label',
  distill: 'distill',
  verify: 'verify',
  exchange: 'exchange',
  risk: 'risk',
  backtest: 'backtest',
  'backtest-result': 'backtest'
}

const WORKFLOW_SCREENS = new Set(Object.keys(PIPELINE_SCREEN_BY_SCREEN))
const REVIEWED_FEED_STATUSES = new Set(['verified', 'analyzed'])

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY)) || null
  } catch {
    return null
  }
}

function mergeDemoFeedFlags(savedFeeds) {
  if (!Array.isArray(savedFeeds)) return FEEDS
  const seed = Object.fromEntries(FEEDS.map((c) => [c.id, c]))
  return savedFeeds.map((c) => {
    const source = seed[c.id]
    return source
      ? { ...c, historyGaps: source.historyGaps, signalDeletion: source.signalDeletion }
      : c
  })
}

function createToast(title, msg, tone) {
  return {
    tone,
    title,
    msg,
    time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  }
}

function isReviewedStatus(status) {
  return REVIEWED_FEED_STATUSES.has(status)
}

async function readSourceState(authToken) {
  const [telegram, feeds] = await Promise.all([
    getTelegramStatus(authToken),
    listFeeds(authToken)
  ])

  return {
    telegram,
    feeds: feeds.feeds || []
  }
}

export function useWorkflowState(authToken) {
  const saved = useRef(authToken ? null : loadState()).current

  const [nav, setNav] = useState('sources')
  const [screen, setScreen] = useState(saved ? saved.screen : 'sources')
  const [telegramConnected, setTelegramConnected] = useState(
    saved ? saved.telegramConnected : false
  )
  const [feeds, setFeeds] = useState(
    saved ? mergeDemoFeedFlags(saved.feeds) : authToken ? [] : FEEDS
  )
  const [activeFeedId, setActiveFeedId] = useState(saved ? saved.activeFeedId : null)
  const [verifyAttempt, setVerifyAttempt] = useState(saved ? saved.verifyAttempt : 1)
  const [bybitConnected, setBybitConnected] = useState(
    saved ? saved.bybitConnected : false
  )
  const [toast, setToast] = useState(null)
  const [backTarget, setBackTarget] = useState(null)
  const [signalsPreset, setSignalsPreset] = useState(null)
  const [backfillMode, setBackfillMode] = useState('resume')

  const prevNavRef = useRef('sources')
  const previousBackfillStatusRef = useRef(null)

  const fireToast = useCallback((tone, title, msg) => {
    setToast(createToast(title, msg, tone))
    setTimeout(() => setToast(null), 4200)
  }, [])

  useEffect(() => {
    if (authToken) return

    localStorage.setItem(
      LS_KEY,
      JSON.stringify({
        screen,
        telegramConnected,
        feeds,
        activeFeedId,
        verifyAttempt,
        bybitConnected
      })
    )
  }, [
    authToken,
    screen,
    telegramConnected,
    feeds,
    activeFeedId,
    verifyAttempt,
    bybitConnected
  ])

  async function refreshSources() {
    if (!authToken) return null

    const sourceState = await readSourceState(authToken)
    setTelegramConnected(sourceState.telegram.connected)
    setFeeds(sourceState.feeds)
    return sourceState
  }

  useEffect(() => {
    if (!authToken) return undefined

    let active = true

    readSourceState(authToken)
      .then((sourceState) => {
        if (!active) return
        setTelegramConnected(sourceState.telegram.connected)
        setFeeds(sourceState.feeds)
      })
      .catch((error) => {
        if (!active) return
        fireToast(
          'rejected',
          'Sources unavailable',
          error?.message || 'Could not load Telegram sources.'
        )
      })

    return () => {
      active = false
    }
  }, [authToken, fireToast])

  const activeFeed = feeds.find((feed) => feed.id === activeFeedId) || null

  function clearToast() {
    setToast(null)
  }

  function patchFeed(id, patch) {
    setFeeds((currentFeeds) =>
      currentFeeds.map((feed) => (feed.id === id ? { ...feed, ...patch } : feed))
    )
  }

  function upsertFeed(feed) {
    setFeeds((currentFeeds) => {
      const exists = currentFeeds.some((currentFeed) => currentFeed.id === feed.id)
      if (exists) {
        return currentFeeds.map((currentFeed) =>
          currentFeed.id === feed.id ? feed : currentFeed
        )
      }
      return [...currentFeeds, feed]
    })
  }

  function goToDeletedSignals(feed) {
    setSignalsPreset({ source: 'all', feed: feed.id, tab: 'deleted', _t: Date.now() })
    setNav('signals')
  }

  function startBackfill(feed) {
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setActiveFeedId(feed.id)
    patchFeed(feed.id, { status: 'backfilling' })
    setScreen('backfill')
  }

  function retryBackfill(feed) {
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setActiveFeedId(feed.id)
    patchFeed(feed.id, { status: 'backfilling' })
    setScreen('backfill')
  }

  function resumeFeed(feed) {
    setActiveFeedId(feed.id)
    if (feed.status === 'analyzed') setScreen('backtest-result')
    else if (feed.status === 'backfilled') setScreen('label')
    else setScreen('label')
  }

  function fetchNewMessages(feed) {
    previousBackfillStatusRef.current = isReviewedStatus(feed.status)
      ? feed.status
      : null
    setBackfillMode('refresh')
    setActiveFeedId(feed.id)
    patchFeed(feed.id, { status: 'backfilling' })
    setScreen('backfill')
    fireToast(
      'info',
      'Fetching new messages',
      `Pulling new messages from ${feed.name}.`
    )
  }

  function refetchFullHistory(feed) {
    previousBackfillStatusRef.current = isReviewedStatus(feed.status)
      ? feed.status
      : null
    setBackfillMode('full')
    setActiveFeedId(feed.id)
    patchFeed(feed.id, { status: 'backfilling' })
    setScreen('backfill')
    fireToast(
      'info',
      'Re-fetching history',
      `Re-pulling the full history of ${feed.name}.`
    )
  }

  function removeFeed(id) {
    setFeeds((currentFeeds) => currentFeeds.filter((feed) => feed.id !== id))
    if (activeFeedId === id) {
      setActiveFeedId(null)
      setScreen('feeds')
    }
  }

  function reviewLabels(feed) {
    setActiveFeedId(feed.id)
    setScreen('label')
  }

  function checkGaps(feed) {
    if (feed.signalDeletion) {
      fireToast(
        'rejected',
        'Signal deletion confirmed',
        `${feed.name} is missing extracted signals — quality is floored to 0.`
      )
    } else if (feed.historyGaps) {
      fireToast(
        'pending',
        'History gaps found',
        `${feed.name} has breaks in its message-ID sequence — some history may be missing.`
      )
    } else {
      fireToast(
        'verified',
        'No gaps found',
        `${feed.name}'s message history is contiguous — no missing IDs.`
      )
    }
  }

  function stopAfterVerify() {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    patchFeed(activeFeedId, { status: 'verified', hasRisk: true })
    setScreen('feeds')
    fireToast(
      'verified',
      'Source verified',
      `${current ? current.name : 'Feed'} is verified and saved. Backtest it any time from the feed options.`
    )
  }

  function backtestFeed(feed) {
    setActiveFeedId(feed.id)
    setScreen('backtest')
  }

  function onBackfillComplete(result) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const previousStatus = previousBackfillStatusRef.current
    const keepsReview = isReviewedStatus(previousStatus)
    const summary =
      typeof result === 'number'
        ? { fetched: result, lastDate: current?.lastDate || null }
        : result || {}
    patchFeed(activeFeedId, {
      status: keepsReview ? previousStatus : 'backfilled',
      fetched: summary.fetched ?? current?.fetched ?? 0,
      lastDate: summary.lastDate ?? current?.lastDate ?? null
    })
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setScreen(keepsReview ? 'feeds' : 'label')
    if (keepsReview) {
      fireToast(
        'verified',
        'Messages fetched',
        `${current ? current.name : 'Feed'} was refreshed. Verification is still saved.`
      )
    }
  }

  function onBackfillCancel(count, date) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const previousStatus = previousBackfillStatusRef.current
    const keepsReview = isReviewedStatus(previousStatus)
    patchFeed(activeFeedId, {
      status: keepsReview ? previousStatus : 'cancelled',
      fetched: count,
      lastDate: date || null
    })
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setScreen('feeds')
    if (keepsReview) {
      fireToast(
        'pending',
        'Fetch cancelled',
        `${current ? current.name : 'Feed'} was not refreshed. Verification is still saved.`
      )
    } else {
      fireToast(
        'pending',
        'Backfill paused',
        `Saved at ${count.toLocaleString()} messages. Retry any time.`
      )
    }
  }

  function onBackfillError(error = {}) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const previousStatus = previousBackfillStatusRef.current
    const keepsReview = isReviewedStatus(previousStatus)
    const fetched = error.fetched ?? current?.fetched ?? 0
    const lastDate = error.lastDate ?? current?.lastDate ?? null
    patchFeed(activeFeedId, {
      status: keepsReview ? previousStatus : 'failed',
      fetched,
      lastDate
    })
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setScreen('feeds')
    if (keepsReview) {
      fireToast(
        'rejected',
        'Fetch failed',
        `${current ? current.name : 'Feed'} was not refreshed. Verification is still saved.`
      )
    } else {
      fireToast(
        'rejected',
        'Backfill failed',
        error?.message || 'Retry when the source is available again.'
      )
    }
  }

  function onBacktestComplete(result) {
    const summary = result || {}
    patchFeed(activeFeedId, {
      status: 'analyzed',
      score: summary.score,
      winRate: summary.winRate,
      pnl: summary.pnl,
      hasRisk: true
    })
    setScreen('feeds')
    fireToast(
      'verified',
      'Source verified',
      `${activeFeed?.name || 'Feed'} scored ${summary.score}/100 and is ready to go live.`
    )
  }

  function requestStepBack(stepId) {
    const order = PIPELINE_STEPS.map((step) => step.id)
    const currentScreen = { 'backtest-result': 'backtest' }[screen] || screen
    if (stepId === 'label' && order.indexOf(currentScreen) > order.indexOf('verify')) {
      setBackTarget(stepId)
      return
    }
    setScreen(stepId)
  }

  function confirmStepBack() {
    const target = backTarget
    setBackTarget(null)
    setScreen(target)
    fireToast(
      'pending',
      'Back to Label',
      'Your labels are kept. Distill and Verify will run again before signals can route.'
    )
  }

  function openSettings() {
    if (nav !== 'settings') prevNavRef.current = nav
    setNav('settings')
  }

  function restoreNav() {
    setNav(prevNavRef.current || 'sources')
  }

  function handleNav(nextNav) {
    setNav(nextNav)
    if (nextNav === 'sources') {
      const inWorkflow = WORKFLOW_SCREENS.has(screen)
      setScreen(telegramConnected ? (inWorkflow ? screen : 'sources') : 'sources')
    }
  }

  function exitToFeeds() {
    setScreen('feeds')
  }

  function exitToSources() {
    setScreen('sources')
  }

  function connectBybit() {
    setBybitConnected(true)
    fireToast('verified', 'Bybit connected', 'Verified signals will route to Bybit.')
  }

  function disconnectBybit() {
    setBybitConnected(false)
    fireToast(
      'rejected',
      'Bybit disconnected',
      'Verified signals are no longer routing to Bybit.'
    )
  }

  function connectTelegram() {
    setTelegramConnected(true)
    setScreen('feeds')
    void refreshSources().catch((error) =>
      fireToast(
        'rejected',
        'Sources unavailable',
        error?.message || 'Could not load Telegram sources.'
      )
    )
    fireToast('verified', 'Telegram connected', 'Pulling your feed list.')
  }

  return {
    nav,
    setNav,
    screen,
    setScreen,
    telegramConnected,
    feeds,
    activeFeedId,
    verifyAttempt,
    setVerifyAttempt,
    bybitConnected,
    toast,
    backTarget,
    signalsPreset,
    backfillMode,
    activeFeed,
    isWorkflow: WORKFLOW_SCREENS.has(screen),
    pipelineStep: PIPELINE_SCREEN_BY_SCREEN[screen] || null,

    goToDeletedSignals,
    startBackfill,
    retryBackfill,
    resumeFeed,
    fetchNewMessages,
    refetchFullHistory,
    reviewLabels,
    removeFeed,
    checkGaps,
    stopAfterVerify,
    backtestFeed,
    onBackfillComplete,
    onBackfillCancel,
    onBackfillError,
    onBacktestComplete,
    requestStepBack,
    confirmStepBack,
    fireToast,
    clearToast,
    openSettings,
    restoreNav,
    handleNav,
    exitToFeeds,
    exitToSources,
    connectBybit,
    disconnectBybit,
    connectTelegram,
    refreshSources,
    upsertFeed,
    setActiveFeedId,
    setBackTarget
  }
}
