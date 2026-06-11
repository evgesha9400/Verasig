import { useState, useEffect, useRef, useLayoutEffect } from 'react'
import { Button, IconButton, ToastStack, Toast, Dialog } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { Shell } from './layout/Shell.jsx'
import { Pipeline, PIPELINE_STEPS } from './features/pipeline/Pipeline.jsx'
import { SourcesView } from './features/sources/SourcesView.jsx'
import { TelegramSetup } from './features/sources/TelegramSetup.jsx'
import { ChatsView } from './features/sources/ChatsView.jsx'
import { SignalsView } from './features/signals/SignalsView.jsx'
import { BackfillView } from './features/pipeline/steps/BackfillView.jsx'
import { LabelView } from './features/pipeline/steps/LabelView.jsx'
import { DistillView } from './features/pipeline/steps/DistillView.jsx'
import { VerifyView } from './features/pipeline/steps/VerifyView.jsx'
import { ExchangeView } from './features/pipeline/steps/ExchangeView.jsx'
import { ExecutionView } from './features/pipeline/steps/ExecutionView.jsx'
import { BacktestView } from './features/pipeline/steps/BacktestView.jsx'
import { ExchangesView } from './features/exchanges/ExchangesView.jsx'
import { SettingsView } from './features/settings/SettingsView.jsx'
import { LoginView } from './features/auth/LoginView.jsx'
import { RegisterView } from './features/auth/RegisterView.jsx'
import { CHATS, MESSAGES } from './data/seed.js'

const THEME_ACCENTS = {
  dark:  ['#B9EE2E', '#CBF457', '#8FB81E', 'rgba(185,238,46,0.28)'],
  light: ['#5197FF', '#82B6FF', '#2F6FE0', 'rgba(81,151,255,0.30)'],
}
const THEME_KEY = 'vrs-theme-1'
function loadTheme() {
  try { return localStorage.getItem(THEME_KEY) || 'dark' } catch { return 'dark' }
}

const LS_KEY = 'vrs-proto-state-1'
function loadState() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || null } catch { return null }
}

const USER_KEY = 'vrs-user-1'
const USER_DEFAULTS = { firstName: 'Mara', lastName: 'Voss', email: 'mara@northwave.io', plan: 'operator', pendingEmail: null, cancelAt: null }
function loadUser() {
  try { return { ...USER_DEFAULTS, ...(JSON.parse(localStorage.getItem(USER_KEY)) || {}) } } catch { return { ...USER_DEFAULTS } }
}

// The marketing site (root domain) links here with ?signup=1 for "Get started".
const MARKETING_URL = import.meta.env.VITE_MARKETING_URL || 'http://localhost:5174'
function initialAuthScreen() {
  try {
    return new URLSearchParams(window.location.search).get('signup') === '1' ? 'register' : 'login'
  } catch { return 'login' }
}

function mergeChatFlags(savedChats) {
  if (!Array.isArray(savedChats)) return CHATS
  const seed = Object.fromEntries(CHATS.map((c) => [c.id, c]))
  return savedChats.map((c) => {
    const s = seed[c.id]
    return s ? { ...c, historyGaps: s.historyGaps, signalDeletion: s.signalDeletion } : c
  })
}

export default function App() {
  const saved = useRef(loadState()).current
  const [theme, setTheme] = useState(loadTheme())
  function changeTheme(next) { setTheme(next); try { localStorage.setItem(THEME_KEY, next) } catch { /* ignore */ } }
  const [nav, setNav] = useState('sources')
  const [user, setUser] = useState(loadUser())
  const prevNavRef = useRef('sources')
  function updateUser(patch) {
    setUser((u) => { const n = { ...u, ...patch }; try { localStorage.setItem(USER_KEY, JSON.stringify(n)) } catch { /* ignore */ } return n })
  }
  function openSettings() { if (nav !== 'settings') prevNavRef.current = nav; setNav('settings') }
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
  const [authScreen, setAuthScreen] = useState(initialAuthScreen) // 'login' | 'register' | null

  function goToDeletedSignals(c) {
    setSignalsPreset({ source: 'all', feed: c.id, tab: 'deleted', _t: Date.now() })
    setNav('signals')
  }

  // persist
  useEffect(() => {
    localStorage.setItem(LS_KEY, JSON.stringify({ screen, telegramConnected, chats, activeChatId, labelsByChat, verifyAttempt, bybitConnected }))
  }, [screen, telegramConnected, chats, activeChatId, labelsByChat, verifyAttempt, bybitConnected])

  // apply theme
  useEffect(() => {
    const root = document.documentElement
    const [a, hover, press, quiet] = THEME_ACCENTS[theme] || THEME_ACCENTS.dark
    root.style.setProperty('--accent', a)
    root.style.setProperty('--accent-hover', hover)
    root.style.setProperty('--accent-press', press)
    root.style.setProperty('--accent-text', hover)
    root.style.setProperty('--accent-quiet', quiet)
    root.style.setProperty('--signal-500', a)
    root.style.setProperty('--signal-400', hover)
    root.style.setProperty('--signal-glow', quiet)
    root.style.setProperty('--verified-500', a)
    root.setAttribute('data-density', 'regular')
    root.setAttribute('data-theme', theme)
    root.setAttribute('data-wide', 'center')
  }, [theme])

  // Any view that renders a persistent right rail (Label, Verify, …) needs the
  // topbar + stepper to center over the work area, not the full main width.
  // The rail can appear/disappear from a child component's INTERNAL state change
  // (e.g. Verify's pass/fail screens) without App re-rendering, so a render-time
  // check goes stale. Watch the DOM itself: recompute on every subtree mutation.
  useLayoutEffect(() => {
    const update = () => {
      const hasRail = !!document.querySelector('.vrs-scroll .vrs-rail')
      document.documentElement.setAttribute('data-rail', hasRail ? 'on' : 'off')
    }
    update()
    const mo = new MutationObserver(update)
    mo.observe(document.body, { childList: true, subtree: true })
    return () => mo.disconnect()
  }, [])

  const activeChat = chats.find((c) => c.id === activeChatId) || null
  const labels = (activeChatId && labelsByChat[activeChatId]) || {}
  // 'modifier' is a legacy label value from an earlier flow — a reply that is a
  // signal IS an update, so it counts as a signal; the link is derived, not labelled.
  const signalCount = Object.values(labels).filter((v) => v === 'signal' || v === 'modifier').length
  const noiseCount = Object.values(labels).filter((v) => v === 'noise').length

  function patchChat(id, patch) {
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c)))
  }
  function fireToast(tone, title, msg) {
    setToast({ tone, title, msg, time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) })
    setTimeout(() => setToast(null), 4200)
  }

  // ---- workflow transitions ----
  function startBackfill(c) { setActiveChatId(c.id); patchChat(c.id, { status: 'backfilling' }); setScreen('backfill') }
  function retryBackfill(c) { setActiveChatId(c.id); patchChat(c.id, { status: 'backfilling' }); setScreen('backfill') }
  function resumeChat(c) {
    setActiveChatId(c.id)
    if (c.status === 'analyzed') setScreen('backtest-result')
    else if (c.status === 'backfilled') setScreen('label')
    else setScreen('label')
  }
  function reanalyze(c) { setActiveChatId(c.id); patchChat(c.id, { status: 'backfilling' }); setScreen('backfill'); fireToast('info', 'Re-backfilling', `Fetching new signals from ${c.name}.`) }
  function restartChat(c) {
    patchChat(c.id, { status: 'new', fetched: 0, lastDate: null, score: null, winRate: null, pnl: null })
    setLabelsByChat((m) => { const n = { ...m }; delete n[c.id]; return n })
    fireToast('rejected', 'Feed reset', `${c.name} backfill and labels deleted.`)
  }
  function checkGaps(c) {
    if (c.signalDeletion) fireToast('rejected', 'Signal deletion confirmed', `${c.name} is missing extracted signals — quality is floored to 0.`)
    else if (c.historyGaps) fireToast('pending', 'History gaps found', `${c.name} has breaks in its message-ID sequence — some history may be missing.`)
    else fireToast('verified', 'No gaps found', `${c.name}'s message history is contiguous — no missing IDs.`)
  }
  // Stop after Verify: save the source as verified without backtesting / connecting an exchange.
  function stopAfterVerify() {
    const c = chats.find((x) => x.id === activeChatId)
    patchChat(activeChatId, { status: 'verified', hasRisk: true })
    setScreen('chats')
    fireToast('verified', 'Source verified', `${c ? c.name : 'Feed'} is verified and saved. Backtest it any time from the feed options.`)
  }
  // Backtest later: pick up a verified-only feed at the exchange step of the happy path.
  function backtestFeed(c) { setActiveChatId(c.id); setScreen('exchange') }

  function onBackfillComplete(total) { patchChat(activeChatId, { status: 'backfilled', fetched: total, lastDate: 'Nov 18, 2025' }); setScreen('label') }
  function onBackfillCancel(count, date) { patchChat(activeChatId, { status: 'cancelled', fetched: count, lastDate: date }); setScreen('chats'); fireToast('pending', 'Backfill paused', `Saved at ${count.toLocaleString()} messages. Retry any time.`) }

  function setLabel(msgId, label) { setLabelsByChat((m) => ({ ...m, [activeChatId]: { ...(m[activeChatId] || {}), [msgId]: label } })) }

  // ---- backward navigation (pipeline stepper) ----
  // Free for review/config steps; going back to Label from beyond Verify
  // invalidates the distilled rules, so that one asks first.
  function requestStepBack(stepId) {
    const order = PIPELINE_STEPS.map((s) => s.id)
    const cur = { 'backtest-result': 'backtest' }[screen] || screen
    if (stepId === 'label' && order.indexOf(cur) > order.indexOf('verify')) { setBackTarget(stepId); return }
    setScreen(stepId)
  }
  function confirmStepBack() {
    const target = backTarget
    setBackTarget(null)
    setScreen(target)
    fireToast('pending', 'Back to Label', 'Your labels are kept. Distill and Verify will run again before routing.')
  }

  // ---- auth early-return ----
  if (authScreen === 'login') {
    return <LoginView onLogin={() => setAuthScreen(null)} onRegister={() => setAuthScreen('register')} />
  }
  if (authScreen === 'register') {
    return <RegisterView onRegister={() => setAuthScreen(null)} onLogin={() => setAuthScreen('login')} />
  }

  // ---- screen rendering ----
  const isWorkflow = ['backfill', 'label', 'distill', 'verify', 'exchange', 'risk', 'backtest', 'backtest-result'].includes(screen)
  const pipelineStep = { backfill: 'backfill', label: 'label', distill: 'distill', verify: 'verify', exchange: 'exchange', risk: 'risk', backtest: 'backtest', 'backtest-result': 'backtest' }[screen]

  function exitToChats() { setScreen('chats') }
  function exitToSources() { setScreen('sources') }

  // top bar title/sub per screen
  let title = 'Sources', subtitle = 'Connect where your signals come from', breadcrumb = null, onExit = null, pipeline = null, body = null, actions = null

  if (nav === 'signals') {
    title = 'Signals'; subtitle = 'Signals extracted from your analyzed feeds'
    body = <SignalsView feeds={chats} initial={signalsPreset} onGoToSources={() => { setNav('sources'); setScreen(telegramConnected ? 'chats' : 'sources') }} />
  } else if (nav === 'exchanges') {
    title = 'Exchanges'; subtitle = 'Where verified signals are routed'
    body = <ExchangesView bybitConnected={bybitConnected} onConnect={() => { setBybitConnected(true); fireToast('verified', 'Bybit connected', 'Verified signals will route to Bybit.') }} onDisconnect={() => { setBybitConnected(false); fireToast('rejected', 'Bybit disconnected', 'Verified signals are no longer routing to Bybit.') }} />
  } else if (nav === 'settings') {
    title = 'Account settings'; subtitle = 'Profile, security & subscription'
    breadcrumb = 'Back'; onExit = () => setNav(prevNavRef.current || 'sources')
    body = <SettingsView user={user} onUpdateUser={updateUser} onToast={fireToast} />
  } else {
    // nav === 'sources'
    if (screen === 'sources') {
      title = 'Sources'; subtitle = 'Connect where your signals come from'
      body = <SourcesView telegramConnected={telegramConnected} chats={chats}
        onConnectTelegram={() => setScreen('tg-setup')} onOpenTelegram={() => setScreen('chats')} />
    } else if (screen === 'tg-setup') {
      title = 'Connect Telegram'; subtitle = 'Source setup'; breadcrumb = 'Sources'; onExit = exitToSources
      body = <TelegramSetup onConnected={() => { setTelegramConnected(true); setScreen('chats'); fireToast('verified', 'Telegram connected', 'Pulling your feed list.') }} onCancel={exitToSources} />
    } else if (screen === 'chats') {
      title = 'Telegram'; subtitle = `${chats.length} feeds · ${chats.filter((c) => c.status === 'analyzed').length} analyzed`; breadcrumb = 'Sources'; onExit = exitToSources
      body = <ChatsView chats={chats} onStartBackfill={startBackfill} onRetry={retryBackfill} onResume={resumeChat} onReanalyze={reanalyze} onRestart={restartChat} onViewDeleted={goToDeletedSignals} onCheckGaps={checkGaps} onBacktest={backtestFeed} />
    } else if (isWorkflow && activeChat) {
      breadcrumb = activeChat.name; onExit = exitToChats
      pipeline = <Pipeline current={pipelineStep} onStepBack={requestStepBack} />
      const stepTitles = {
        backfill: ['Backfill', 'Pulling message history'],
        label: ['Label', 'Teach Verasig what a signal looks like'],
        distill: ['Distill', 'Generating filter rules'],
        verify: ['Verify', 'Confirm the rules hold'],
        exchange: ['Exchange', 'Route verified signals'],
        risk: ['Execution', 'Size, entry and exit for every verified signal'],
        backtest: ['Backtest', 'Simulating performance'],
        'backtest-result': ['Signal quality', 'Backtest results'],
      }
      title = stepTitles[screen][0]; subtitle = `${activeChat.name} · ${stepTitles[screen][1]}`

      if (screen === 'backfill') body = <BackfillView chat={activeChat} onCancel={onBackfillCancel} onComplete={onBackfillComplete} />
      else if (screen === 'label') body = <LabelView messages={MESSAGES} labels={labels} onLabel={setLabel} signalCount={signalCount} noiseCount={noiseCount} onDistill={() => setScreen('distill')} key={'label-' + verifyAttempt} />
      else if (screen === 'distill') body = <DistillView onComplete={() => setScreen('verify')} />
      else if (screen === 'verify') body = <VerifyView key={'verify-' + verifyAttempt} attempt={verifyAttempt} onPass={() => setScreen('exchange')} onStop={stopAfterVerify} onLoop={() => { setVerifyAttempt((a) => a + 1); setScreen('label'); fireToast('pending', 'Refining rules', "Label a few more, then we'll re-verify.") }} />
      else if (screen === 'exchange') body = <ExchangeView bybitConnected={bybitConnected} onConnected={() => { setBybitConnected(true); setScreen('risk') }} />
      else if (screen === 'risk') body = <ExecutionView layout="flow" controls="segmented" hasRisk={true} onRun={() => setScreen('backtest')} />
      else if (screen === 'backtest') body = <BacktestView chat={activeChat} onComplete={(sd) => { patchChat(activeChatId, { status: 'analyzed', score: sd.score, winRate: sd.winRate, pnl: sd.pnl, hasRisk: true }); setScreen('chats'); fireToast('verified', 'Source verified', `${activeChat.name} scored ${sd.score}/100 and is ready to go live.`) }} />
      else if (screen === 'backtest-result') body = <BacktestView chat={activeChat} skipRun={true} onComplete={() => setScreen('chats')} />
    } else {
      title = 'Sources'
      body = <SourcesView telegramConnected={telegramConnected} chats={chats} onConnectTelegram={() => setScreen('tg-setup')} onOpenTelegram={() => setScreen('chats')} />
    }
  }

  // top-right actions
  if (nav === 'sources' && screen === 'chats') {
    actions = <IconButton label="Refresh feeds" onClick={() => fireToast('info', 'Refreshed', 'Feed list synced with Telegram.')}><Icon name="refresh" size={16} /></IconButton>
  }

  function handleNav(id) { setNav(id); if (id === 'sources') setScreen(telegramConnected ? (isWorkflow ? screen : 'sources') : 'sources') }

  return (
    <>
      <Shell nav={nav} onNavigate={handleNav} title={title} subtitle={subtitle} breadcrumb={breadcrumb} onExit={onExit} actions={actions} pipeline={pipeline}
        theme={theme} onThemeChange={changeTheme} onLogout={() => { window.location.href = MARKETING_URL }}
        user={user} onOpenSettings={openSettings}>
        {body}
      </Shell>

      <Dialog
        open={!!backTarget}
        onClose={() => setBackTarget(null)}
        title="Go back to Label?"
        description="Changing labels invalidates the distilled ruleset."
        icon={<Icon name="alert" size={19} />}
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setBackTarget(null)}>Stay here</Button>
          <Button variant="primary" size="sm" onClick={confirmStepBack}>Go back to Label</Button>
        </>}
      >
        Your existing labels are kept, but Distill and Verify will run again before signals can route. Exchange and execution settings are unaffected.
      </Dialog>

      {toast && (
        <ToastStack>
          <Toast tone={toast.tone} title={toast.title} time={toast.time} onClose={() => setToast(null)}>{toast.msg}</Toast>
        </ToastStack>
      )}
    </>
  )
}
