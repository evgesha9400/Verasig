import { useCallback, useEffect, useRef, useState } from 'react'
import { listFeeds } from '../../shared/api/feedsApi.js'
import { getTelegramStatus } from '../../shared/api/telegramApi.js'
import { PIPELINE_STEPS } from '../../domain/workflow/pipelineSteps.js'
import { landingStepForFeed } from '../../domain/workflow/stepAccess.js'
import { confirmMining } from '../../shared/api/mineApi.js'
import { FEEDS } from '../../domain/demo-data/seed.js'

const LS_KEY = 'vrs-proto-state-2'

const PIPELINE_SCREEN_BY_SCREEN = {
  backfill: 'backfill',
  mine: 'mine',
  review: 'review',
  verify: 'verify',
  exchange: 'exchange',
  backtest: 'backtest',
  execution: 'execution',
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
    return source ? { ...c, signalDeletion: source.signalDeletion } : c
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

function isReviewedFeed(feed) {
  return Boolean(feed) && (isReviewedStatus(feed.status) || feed.hasRisk)
}

export function mergeReviewedFeedState(currentFeeds, refreshedFeeds) {
  if (!Array.isArray(currentFeeds)) return refreshedFeeds
  if (!Array.isArray(refreshedFeeds)) return refreshedFeeds
  const currentById = new Map(currentFeeds.map((feed) => [feed.id, feed]))
  return refreshedFeeds.map((refreshedFeed) => {
    const currentFeed = currentById.get(refreshedFeed.id)
    if (!currentFeed) return refreshedFeed
    if (!isReviewedFeed(currentFeed)) return refreshedFeed
    if (isReviewedFeed(refreshedFeed)) {
      return {
        ...refreshedFeed,
        hasRisk:
          refreshedFeed.hasRisk ||
          currentFeed.hasRisk ||
          isReviewedStatus(refreshedFeed.status)
      }
    }
    return {
      ...refreshedFeed,
      status: currentFeed.status,
      hasRisk: true
    }
  })
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

export function useWorkflowState(authToken, plan) {
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
  const [bybitConnected, setBybitConnected] = useState(
    saved ? saved.bybitConnected : false
  )
  const [toast, setToast] = useState(null)
  const [backTarget, setBackTarget] = useState(null)
  const [signalsPreset, setSignalsPreset] = useState(null)
  const [backfillMode, setBackfillMode] = useState('resume')
  const [backfillDepth, setBackfillDepth] = useState('1y')

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
        bybitConnected
      })
    )
  }, [authToken, screen, telegramConnected, feeds, activeFeedId, bybitConnected])

  async function refreshSources() {
    if (!authToken) return null

    const sourceState = await readSourceState(authToken)
    setTelegramConnected(sourceState.telegram.connected)
    setFeeds((currentFeeds) => mergeReviewedFeedState(currentFeeds, sourceState.feeds))
    return sourceState
  }

  useEffect(() => {
    if (!authToken) return undefined

    let active = true

    readSourceState(authToken)
      .then((sourceState) => {
        if (!active) return
        setTelegramConnected(sourceState.telegram.connected)
        setFeeds((currentFeeds) =>
          mergeReviewedFeedState(currentFeeds, sourceState.feeds)
        )
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

  function startBackfill(feed, depth = '1y') {
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setBackfillDepth(depth)
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
    const landing = landingStepForFeed(feed, plan)
    // An analyzed feed that can reach Backtest opens its results, not the runner.
    if (feed.status === 'analyzed' && landing === 'backtest') {
      setScreen('backtest-result')
      return
    }
    setScreen(landing)
  }

  // The whole feed row is clickable: open it at its latest stage. New feeds start
  // a backfill (default depth; choose another later via the gear); failed/cancelled
  // retry; an in-progress backfill shows live progress; the rest resume their stage.
  function openFeed(feed) {
    if (feed.status === 'new') return startBackfill(feed)
    if (feed.status === 'failed' || feed.status === 'cancelled') {
      return retryBackfill(feed)
    }
    if (feed.status === 'backfilling') {
      setActiveFeedId(feed.id)
      setScreen('backfill')
      return
    }
    resumeFeed(feed)
  }

  function fetchNewMessages(feed) {
    previousBackfillStatusRef.current = isReviewedFeed(feed) ? feed.status : null
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

  function refetchFullHistory(feed, depth = '1y') {
    previousBackfillStatusRef.current = isReviewedFeed(feed) ? feed.status : null
    setBackfillMode('full')
    setBackfillDepth(depth)
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

  function reopenMining(feed) {
    setActiveFeedId(feed.id)
    setScreen('mine')
  }

  function checkGaps(feed) {
    if (feed.signalDeletion) {
      fireToast(
        'rejected',
        'Signal deletion confirmed',
        `${feed.name} is missing extracted signals — quality is floored to 0.`
      )
    } else {
      fireToast(
        'verified',
        'No signal deletions',
        `${feed.name} has no confirmed deleted signals.`
      )
    }
  }

  // Persist the accepted templates server-side: the backend re-mines (identical
  // template keys by parity), extracts + stores the signals, and marks the feed
  // verified. Optimistic UI patches first; this reconciles from the server.
  async function persistVerified(acceptedTemplateKeys) {
    if (!authToken || !activeFeedId) return
    try {
      await confirmMining(authToken, activeFeedId, acceptedTemplateKeys || [])
      await refreshSources()
    } catch (error) {
      fireToast(
        'rejected',
        'Could not save verification',
        error?.message || 'Try again in a moment.'
      )
    }
  }

  function stopAfterVerify(acceptedTemplateKeys = []) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    patchFeed(activeFeedId, { status: 'verified', hasRisk: true })
    setScreen('feeds')
    fireToast(
      'verified',
      'Source verified',
      `${current ? current.name : 'Feed'} is verified and saved. Backtest it any time from the feed options.`
    )
    void persistVerified(acceptedTemplateKeys)
  }

  function routeAfterVerify(acceptedTemplateKeys = []) {
    patchFeed(activeFeedId, { status: 'verified', hasRisk: true })
    setScreen('exchange')
    void persistVerified(acceptedTemplateKeys)
  }

  function backtestFeed(feed) {
    setActiveFeedId(feed.id)
    setScreen('backtest')
  }

  function onBackfillComplete(result) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const previousStatus = previousBackfillStatusRef.current
    const keepsReview = previousStatus !== null
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
    setScreen(keepsReview ? 'feeds' : 'mine')
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
    const keepsReview = previousStatus !== null
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
    const keepsReview = previousStatus !== null
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
    if (stepId === 'mine' && order.indexOf(currentScreen) > order.indexOf('mine')) {
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
      'Back to Mining',
      'Your family decisions are kept. Rules will be recompiled and re-audited before signals can route again.'
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
    bybitConnected,
    toast,
    backTarget,
    signalsPreset,
    backfillMode,
    backfillDepth,
    activeFeed,
    isWorkflow: WORKFLOW_SCREENS.has(screen),
    pipelineStep: PIPELINE_SCREEN_BY_SCREEN[screen] || null,

    goToDeletedSignals,
    startBackfill,
    retryBackfill,
    resumeFeed,
    openFeed,
    fetchNewMessages,
    refetchFullHistory,
    reopenMining,
    removeFeed,
    checkGaps,
    stopAfterVerify,
    routeAfterVerify,
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
