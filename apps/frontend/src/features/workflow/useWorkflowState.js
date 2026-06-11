import { useEffect, useRef, useState } from 'react'
import { CHATS } from '../../data/seed.js'
import { PIPELINE_STEPS } from '../pipeline/Pipeline.jsx'

const LS_KEY = 'vrs-proto-state-1'

const PIPELINE_SCREEN_BY_SCREEN = {
  backfill: 'backfill',
  label: 'label',
  distill: 'distill',
  verify: 'verify',
  exchange: 'exchange',
  risk: 'risk',
  backtest: 'backtest',
  'backtest-result': 'backtest',
}

const WORKFLOW_SCREENS = new Set(Object.keys(PIPELINE_SCREEN_BY_SCREEN))

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY)) || null
  } catch {
    return null
  }
}

function mergeChatFlags(savedChats) {
  if (!Array.isArray(savedChats)) return CHATS
  const seed = Object.fromEntries(CHATS.map((c) => [c.id, c]))
  return savedChats.map((c) => {
    const source = seed[c.id]
    return source ? { ...c, historyGaps: source.historyGaps, signalDeletion: source.signalDeletion } : c
  })
}

function createToast(title, msg, tone) {
  return {
    tone,
    title,
    msg,
    time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
  }
}

export function useWorkflowState() {
  const saved = useRef(loadState()).current

  const [nav, setNav] = useState('sources')
  const [screen, setScreen] = useState(saved ? saved.screen : 'sources')
  const [telegramConnected, setTelegramConnected] = useState(saved ? saved.telegramConnected : false)
  const [chats, setChats] = useState(saved ? mergeChatFlags(saved.chats) : CHATS)
  const [activeChatId, setActiveChatId] = useState(saved ? saved.activeChatId : null)
  const [labelsByChat, setLabelsByChat] = useState(saved ? saved.labelsByChat : {})
  const [verifyAttempt, setVerifyAttempt] = useState(saved ? saved.verifyAttempt : 1)
  const [bybitConnected, setBybitConnected] = useState(saved ? saved.bybitConnected : false)
  const [toast, setToast] = useState(null)
  const [backTarget, setBackTarget] = useState(null)
  const [signalsPreset, setSignalsPreset] = useState(null)

  const prevNavRef = useRef('sources')

  useEffect(() => {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify({
        screen,
        telegramConnected,
        chats,
        activeChatId,
        labelsByChat,
        verifyAttempt,
        bybitConnected,
      }),
    )
  }, [screen, telegramConnected, chats, activeChatId, labelsByChat, verifyAttempt, bybitConnected])

  const activeChat = chats.find((chat) => chat.id === activeChatId) || null
  const labels = (activeChatId && labelsByChat[activeChatId]) || {}
  const signalCount = Object.values(labels).filter((value) => value === 'signal' || value === 'modifier').length
  const noiseCount = Object.values(labels).filter((value) => value === 'noise').length

  function fireToast(tone, title, msg) {
    setToast(createToast(title, msg, tone))
    setTimeout(() => setToast(null), 4200)
  }

  function clearToast() {
    setToast(null)
  }

  function patchChat(id, patch) {
    setChats((currentChats) => currentChats.map((chat) => (chat.id === id ? { ...chat, ...patch } : chat)))
  }

  function setLabel(msgId, label) {
    setLabelsByChat((current) => ({
      ...current,
      [activeChatId]: {
        ...(current[activeChatId] || {}),
        [msgId]: label,
      },
    }))
  }

  function goToDeletedSignals(chat) {
    setSignalsPreset({ source: 'all', feed: chat.id, tab: 'deleted', _t: Date.now() })
    setNav('signals')
  }

  function startBackfill(chat) {
    setActiveChatId(chat.id)
    patchChat(chat.id, { status: 'backfilling' })
    setScreen('backfill')
  }

  function retryBackfill(chat) {
    setActiveChatId(chat.id)
    patchChat(chat.id, { status: 'backfilling' })
    setScreen('backfill')
  }

  function resumeChat(chat) {
    setActiveChatId(chat.id)
    if (chat.status === 'analyzed') setScreen('backtest-result')
    else if (chat.status === 'backfilled') setScreen('label')
    else setScreen('label')
  }

  function reanalyze(chat) {
    setActiveChatId(chat.id)
    patchChat(chat.id, { status: 'backfilling' })
    setScreen('backfill')
    fireToast('info', 'Re-backfilling', `Fetching new signals from ${chat.name}.`)
  }

  function restartChat(chat) {
    patchChat(chat.id, {
      status: 'new',
      fetched: 0,
      lastDate: null,
      score: null,
      winRate: null,
      pnl: null,
    })
    setLabelsByChat((current) => {
      const next = { ...current }
      delete next[chat.id]
      return next
    })
    fireToast('rejected', 'Feed reset', `${chat.name} backfill and labels deleted.`)
  }

  function checkGaps(chat) {
    if (chat.signalDeletion) {
      fireToast('rejected', 'Signal deletion confirmed', `${chat.name} is missing extracted signals — quality is floored to 0.`)
    } else if (chat.historyGaps) {
      fireToast('pending', 'History gaps found', `${chat.name} has breaks in its message-ID sequence — some history may be missing.`)
    } else {
      fireToast('verified', 'No gaps found', `${chat.name}'s message history is contiguous — no missing IDs.`)
    }
  }

  function stopAfterVerify() {
    const current = chats.find((chat) => chat.id === activeChatId)
    patchChat(activeChatId, { status: 'verified', hasRisk: true })
    setScreen('chats')
    fireToast('verified', 'Source verified', `${current ? current.name : 'Feed'} is verified and saved. Backtest it any time from the feed options.`)
  }

  function backtestFeed(chat) {
    setActiveChatId(chat.id)
    setScreen('exchange')
  }

  function onBackfillComplete(total) {
    patchChat(activeChatId, {
      status: 'backfilled',
      fetched: total,
      lastDate: 'Nov 18, 2025',
    })
    setScreen('label')
  }

  function onBackfillCancel(count, date) {
    patchChat(activeChatId, {
      status: 'cancelled',
      fetched: count,
      lastDate: date,
    })
    setScreen('chats')
    fireToast('pending', 'Backfill paused', `Saved at ${count.toLocaleString()} messages. Retry any time.`)
  }

  function onBacktestComplete(result) {
    const summary = result || {}
    patchChat(activeChatId, {
      status: 'analyzed',
      score: summary.score,
      winRate: summary.winRate,
      pnl: summary.pnl,
      hasRisk: true,
    })
    setScreen('chats')
    fireToast('verified', 'Source verified', `${activeChat?.name || 'Feed'} scored ${summary.score}/100 and is ready to go live.`)
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
    fireToast('pending', 'Back to Label', 'Your labels are kept. Distill and Verify will run again before signals can route.')
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

  function exitToChats() {
    setScreen('chats')
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
    fireToast('rejected', 'Bybit disconnected', 'Verified signals are no longer routing to Bybit.')
  }

  function connectTelegram() {
    setTelegramConnected(true)
    setScreen('chats')
    fireToast('verified', 'Telegram connected', 'Pulling your feed list.')
  }

  return {
    nav,
    setNav,
    screen,
    setScreen,
    telegramConnected,
    chats,
    activeChatId,
    labelsByChat,
    verifyAttempt,
    setVerifyAttempt,
    bybitConnected,
    toast,
    backTarget,
    signalsPreset,
    activeChat,
    labels,
    signalCount,
    noiseCount,
    isWorkflow: WORKFLOW_SCREENS.has(screen),
    pipelineStep: PIPELINE_SCREEN_BY_SCREEN[screen] || null,

    goToDeletedSignals,
    startBackfill,
    retryBackfill,
    resumeChat,
    reanalyze,
    restartChat,
    checkGaps,
    stopAfterVerify,
    backtestFeed,
    onBackfillComplete,
    onBackfillCancel,
    setLabel,
    onBacktestComplete,
    requestStepBack,
    confirmStepBack,
    fireToast,
    clearToast,
    openSettings,
    restoreNav,
    handleNav,
    exitToChats,
    exitToSources,
    connectBybit,
    disconnectBybit,
    connectTelegram,
    setActiveChatId,
    setBackTarget,
  }
}
