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
  const toastTimerRef = useRef(null)
  const confirmationRef = useRef(null)

  const fireToast = useCallback((tone, title, msg) => {
    setToast(createToast(title, msg, tone))
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast(null), 4200)
  }, [])

  useEffect(
    () => () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    },
    []
  )

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

  // Every backfill entry point does the same six things; they differ only in the
  // mode, whether a reviewed feed keeps its status (refresh/full preserve it so a
  // completed fetch lands back on the reviewed feed, not a re-mine), an optional
  // depth, and an optional kickoff toast.
  function beginBackfill({
    feed,
    mode,
    depth = null,
    keepStatus = false,
    toast = null
  }) {
    previousBackfillStatusRef.current =
      keepStatus && isReviewedFeed(feed) ? feed.status : null
    setBackfillMode(mode)
    if (depth != null) setBackfillDepth(depth)
    setActiveFeedId(feed.id)
    patchFeed(feed.id, { status: 'backfilling' })
    setScreen('backfill')
    if (toast) fireToast(...toast)
  }

  function startBackfill(feed, depth = '1y') {
    beginBackfill({ feed, mode: 'resume', depth })
  }

  function retryBackfill(feed) {
    beginBackfill({ feed, mode: 'resume' })
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
    beginBackfill({
      feed,
      mode: 'refresh',
      keepStatus: true,
      toast: [
        'info',
        'Fetching new messages',
        `Pulling new messages from ${feed.name}.`
      ]
    })
  }

  function refetchFullHistory(feed, depth = '1y') {
    beginBackfill({
      feed,
      mode: 'full',
      depth,
      keepStatus: true,
      toast: [
        'info',
        'Re-fetching history',
        `Re-pulling the full history of ${feed.name}.`
      ]
    })
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

  function finishVerification(destination) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    setScreen(destination)
    fireToast(
      'verified',
      'Source verified',
      `${current ? current.name : 'Feed'} is verified and saved. Backtest it any time from the feed options.`
    )
  }

  async function confirmAuthenticatedVerification(
    reviewId,
    acceptedTemplateKeys,
    destination
  ) {
    const confirmation = await confirmMining(
      authToken,
      activeFeedId,
      reviewId,
      acceptedTemplateKeys
    )
    if (confirmation?.feedStatus !== 'verified') {
      throw new Error('The server did not confirm this feed as verified.')
    }

    const sourceState = await refreshSources()
    const confirmedFeed = sourceState.feeds.find((feed) => feed.id === activeFeedId)
    if (confirmedFeed?.status !== 'verified') {
      throw new Error('The server did not confirm this feed as verified.')
    }

    finishVerification(destination)
    return { confirmation, sourceState }
  }

  async function confirmDemoVerification(destination) {
    patchFeed(activeFeedId, { status: 'verified', hasRisk: true })
    finishVerification(destination)
  }

  function confirmVerification({
    reviewId,
    acceptedTemplateKeys = [],
    destination = 'feeds'
  }) {
    if (!activeFeedId) {
      return Promise.reject(new Error('Select a feed before confirming verification.'))
    }
    if (authToken && !reviewId) {
      return Promise.reject(
        new Error('Re-mine this feed before confirming verification.')
      )
    }
    if (confirmationRef.current) return confirmationRef.current

    const command = authToken
      ? confirmAuthenticatedVerification(reviewId, acceptedTemplateKeys, destination)
      : confirmDemoVerification(destination)
    confirmationRef.current = command.finally(() => {
      confirmationRef.current = null
    })
    return confirmationRef.current
  }

  function backtestFeed(feed) {
    setActiveFeedId(feed.id)
    setScreen('backtest')
  }

  // The three backfill outcomes share one shape: patch the feed to its terminal
  // status (or restore the reviewed status a refresh/full run preserved), clear the
  // resume state, route, and toast. `fetched`/`lastDate`, the fresh-run terminal
  // status + screen, and the toasts are all the handler supplies. Toasts are built
  // from `current` (the active feed) so the copy can name it.
  function finishBackfill({
    terminalStatus,
    fetched,
    lastDate,
    screenWhenFresh,
    toastFresh = null,
    toastKept = null
  }) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const keepsReview = previousBackfillStatusRef.current !== null
    patchFeed(activeFeedId, {
      status: keepsReview ? previousBackfillStatusRef.current : terminalStatus,
      fetched,
      lastDate
    })
    previousBackfillStatusRef.current = null
    setBackfillMode('resume')
    setScreen(keepsReview ? 'feeds' : screenWhenFresh)
    const toast = keepsReview ? toastKept : toastFresh
    if (toast) fireToast(...toast(current))
  }

  function onBackfillComplete(result) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    const summary =
      typeof result === 'number'
        ? { fetched: result, lastDate: current?.lastDate || null }
        : result || {}
    finishBackfill({
      terminalStatus: 'backfilled',
      fetched: summary.fetched ?? current?.fetched ?? 0,
      lastDate: summary.lastDate ?? current?.lastDate ?? null,
      screenWhenFresh: 'mine',
      toastKept: (feed) => [
        'verified',
        'Messages fetched',
        `${feed ? feed.name : 'Feed'} was refreshed. Verification is still saved.`
      ]
    })
  }

  function onBackfillCancel(count, date) {
    finishBackfill({
      terminalStatus: 'cancelled',
      fetched: count,
      lastDate: date || null,
      screenWhenFresh: 'feeds',
      toastFresh: () => [
        'pending',
        'Backfill paused',
        `Saved at ${count.toLocaleString()} messages. Retry any time.`
      ],
      toastKept: (feed) => [
        'pending',
        'Fetch cancelled',
        `${feed ? feed.name : 'Feed'} was not refreshed. Verification is still saved.`
      ]
    })
  }

  function onBackfillError(error = {}) {
    const current = feeds.find((feed) => feed.id === activeFeedId)
    finishBackfill({
      terminalStatus: 'failed',
      fetched: error.fetched ?? current?.fetched ?? 0,
      lastDate: error.lastDate ?? current?.lastDate ?? null,
      screenWhenFresh: 'feeds',
      toastFresh: () => [
        'rejected',
        'Backfill failed',
        error?.message || 'Retry when the source is available again.'
      ],
      toastKept: (feed) => [
        'rejected',
        'Fetch failed',
        `${feed ? feed.name : 'Feed'} was not refreshed. Verification is still saved.`
      ]
    })
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
    confirmVerification,
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
