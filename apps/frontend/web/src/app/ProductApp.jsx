import { useState, useEffect, useLayoutEffect } from 'react'
import {
  Button,
  IconButton,
  ToastStack,
  Toast,
  Dialog,
  useTheme
} from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { Shell } from './layout/Shell.jsx'
import { Pipeline } from '../features/pipeline/Pipeline.jsx'
import { SourcesView } from '../features/sources/SourcesView.jsx'
import { TelegramSetup } from '../features/sources/TelegramSetup.jsx'
import { ChatsView } from '../features/sources/ChatsView.jsx'
import { SignalsView } from '../features/signals/SignalsView.jsx'
import { BackfillView } from '../features/pipeline/steps/BackfillView.jsx'
import { LabelView } from '../features/pipeline/steps/LabelView.jsx'
import { DistillView } from '../features/pipeline/steps/DistillView.jsx'
import { VerifyView } from '../features/pipeline/steps/VerifyView.jsx'
import { ExchangeView } from '../features/pipeline/steps/ExchangeView.jsx'
import { ExecutionView } from '../features/pipeline/steps/ExecutionView.jsx'
import { BacktestView } from '../features/pipeline/steps/BacktestView.jsx'
import { ExchangesView } from '../features/exchanges/ExchangesView.jsx'
import { SettingsView } from '../features/settings/SettingsView.jsx'
import { useWorkflowState } from './workflow/useWorkflowState.js'
import {
  connectTelegram as connectTelegramApi,
  verifyTelegram
} from '../shared/api/telegramApi.js'
import {
  cancelBackfill,
  createChat,
  startBackfill as startBackfillJob,
  streamBackfillProgress
} from '../shared/api/chatsApi.js'
import { MESSAGES } from '../domain/demo-data/seed.js'
import './app.css'

const USER_DEFAULTS = {
  firstName: 'Mara',
  lastName: 'Voss',
  email: 'mara@northwave.io',
  plan: 'operator',
  pendingEmail: null,
  cancelAt: null
}

function mergeUserDefaults(user) {
  return { ...USER_DEFAULTS, ...(user || {}) }
}

export function ProductApp({ authToken, user: sessionUser, onLogout }) {
  const [theme, setTheme] = useTheme()

  const [user, setUser] = useState(() => mergeUserDefaults(sessionUser))

  useEffect(() => {
    setUser(mergeUserDefaults(sessionUser))
  }, [sessionUser])

  function updateUser(patch) {
    setUser((current) => {
      return { ...current, ...patch }
    })
  }

  const {
    nav,
    setNav,
    screen,
    telegramConnected,
    chats,
    activeChat,
    labels,
    signalCount,
    noiseCount,
    verifyAttempt,
    setVerifyAttempt,
    setScreen,
    bybitConnected,
    toast,
    clearToast,
    fireToast,
    backTarget,
    signalsPreset,
    isWorkflow,
    pipelineStep,
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
    onBacktestComplete,
    setLabel,
    requestStepBack,
    confirmStepBack,
    openSettings,
    restoreNav,
    handleNav,
    exitToChats,
    exitToSources,
    connectBybit,
    disconnectBybit,
    connectTelegram: markTelegramConnected,
    refreshSources,
    upsertChat,
    setBackTarget
  } = useWorkflowState(authToken)

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-density', 'regular')
    root.setAttribute('data-wide', 'center')
  }, [])

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

  let title = 'Sources'
  let subtitle = 'Connect where your signals come from'
  let breadcrumb = null
  let onExit = null
  let pipeline = null
  let body = null
  let actions = null

  async function addTelegramChat(tag) {
    const chat = await createChat(authToken, tag)
    upsertChat(chat)
    fireToast('verified', 'Feed added', `${chat.name} is ready to backfill.`)
  }

  function completeBackfill(total) {
    onBackfillComplete(total)
    void refreshSources().catch(() => {})
  }

  if (nav === 'signals') {
    title = 'Signals'
    subtitle = 'Signals extracted from your analyzed feeds'
    body = (
      <SignalsView
        feeds={chats}
        initial={signalsPreset}
        onGoToSources={() => {
          setNav('sources')
          setScreen(telegramConnected ? 'chats' : 'sources')
        }}
      />
    )
  } else if (nav === 'exchanges') {
    title = 'Exchanges'
    subtitle = 'Where verified signals are routed'
    body = (
      <ExchangesView
        bybitConnected={bybitConnected}
        onConnect={() => connectBybit()}
        onDisconnect={() => disconnectBybit()}
      />
    )
  } else if (nav === 'settings') {
    title = 'Account settings'
    subtitle = 'Profile, security & subscription'
    breadcrumb = 'Back'
    onExit = () => restoreNav()
    body = (
      <SettingsView
        authToken={authToken}
        user={user}
        onUpdateUser={updateUser}
        onToast={(...toastProps) => fireToast(...toastProps)}
      />
    )
  } else if (screen === 'sources') {
    title = 'Sources'
    subtitle = 'Connect where your signals come from'
    body = (
      <SourcesView
        telegramConnected={telegramConnected}
        chats={chats}
        onConnectTelegram={() => setScreen('tg-setup')}
        onOpenTelegram={() => setScreen('chats')}
      />
    )
  } else if (screen === 'tg-setup') {
    title = 'Connect Telegram'
    subtitle = 'Source setup'
    breadcrumb = 'Sources'
    onExit = exitToSources
    body = (
      <TelegramSetup
        onConnect={(credentials) => connectTelegramApi(authToken, credentials)}
        onVerify={(code, password) => verifyTelegram(authToken, code, password)}
        onConnected={() => markTelegramConnected()}
        onCancel={exitToSources}
      />
    )
  } else if (screen === 'chats') {
    title = 'Telegram'
    subtitle = `${chats.length} feeds · ${chats.filter((c) => c.status === 'analyzed').length} analyzed`
    breadcrumb = 'Sources'
    onExit = exitToSources
    body = (
      <ChatsView
        chats={chats}
        onStartBackfill={startBackfill}
        onRetry={retryBackfill}
        onResume={resumeChat}
        onReanalyze={reanalyze}
        onRestart={restartChat}
        onViewDeleted={goToDeletedSignals}
        onCheckGaps={checkGaps}
        onBacktest={backtestFeed}
        onAddChat={addTelegramChat}
      />
    )
  } else if (isWorkflow && activeChat) {
    breadcrumb = activeChat.name
    onExit = exitToChats
    pipeline = <Pipeline current={pipelineStep} onStepBack={requestStepBack} />

    const stepTitles = {
      backfill: ['Backfill', 'Pulling message history'],
      label: ['Label', 'Teach Verasig what a signal looks like'],
      distill: ['Distill', 'Generating filter rules'],
      verify: ['Verify', 'Confirm the rules hold'],
      exchange: ['Exchange', 'Route verified signals'],
      risk: ['Execution', 'Size, entry and exit for every verified signal'],
      backtest: ['Backtest', 'Simulating performance'],
      'backtest-result': ['Signal quality', 'Backtest results']
    }

    title = stepTitles[screen][0]
    subtitle = `${activeChat.name} · ${stepTitles[screen][1]}`

    if (screen === 'backfill') {
      body = (
        <BackfillView
          chat={activeChat}
          onStart={(chatId) => startBackfillJob(authToken, chatId)}
          onStream={(chatId, handlers) =>
            streamBackfillProgress(authToken, chatId, handlers)
          }
          onCancelBackfill={(chatId) => cancelBackfill(authToken, chatId)}
          onCancel={onBackfillCancel}
          onComplete={completeBackfill}
        />
      )
    } else if (screen === 'label') {
      body = (
        <LabelView
          messages={MESSAGES}
          labels={labels}
          onLabel={setLabel}
          signalCount={signalCount}
          noiseCount={noiseCount}
          onDistill={() => setScreen('distill')}
          key={`label-${verifyAttempt}`}
        />
      )
    } else if (screen === 'distill') {
      body = <DistillView onComplete={() => setScreen('verify')} />
    } else if (screen === 'verify') {
      body = (
        <VerifyView
          key={`verify-${verifyAttempt}`}
          attempt={verifyAttempt}
          onPass={() => setScreen('exchange')}
          onStop={stopAfterVerify}
          onLoop={() => {
            setVerifyAttempt((a) => a + 1)
            setScreen('label')
            fireToast(
              'pending',
              'Refining rules',
              "Label a few more, then we'll re-verify."
            )
          }}
        />
      )
    } else if (screen === 'exchange') {
      body = (
        <ExchangeView
          bybitConnected={bybitConnected}
          onConnected={() => {
            connectBybit()
            setScreen('risk')
          }}
        />
      )
    } else if (screen === 'risk') {
      body = (
        <ExecutionView
          layout="flow"
          controls="segmented"
          hasRisk={true}
          onRun={() => setScreen('backtest')}
        />
      )
    } else if (screen === 'backtest') {
      body = (
        <BacktestView chat={activeChat} onComplete={(sd) => onBacktestComplete(sd)} />
      )
    } else if (screen === 'backtest-result') {
      body = (
        <BacktestView
          chat={activeChat}
          skipRun={true}
          onComplete={() => setScreen('chats')}
        />
      )
    }
  } else {
    title = 'Sources'
    body = (
      <SourcesView
        telegramConnected={telegramConnected}
        chats={chats}
        onConnectTelegram={() => setScreen('tg-setup')}
        onOpenTelegram={() => setScreen('chats')}
      />
    )
  }

  if (nav === 'sources' && screen === 'chats') {
    actions = (
      <IconButton
        label="Refresh feeds"
        onClick={() => {
          void refreshSources()
            .then(() => {
              fireToast('info', 'Refreshed', 'Feed list synced with Telegram.')
            })
            .catch((error) => {
              fireToast(
                'rejected',
                'Refresh failed',
                error?.message || 'Could not sync Telegram feeds.'
              )
            })
        }}
      >
        <Icon name="refresh" size={16} />
      </IconButton>
    )
  }

  return (
    <>
      <Shell
        nav={nav}
        onNavigate={handleNav}
        title={title}
        subtitle={subtitle}
        breadcrumb={breadcrumb}
        onExit={onExit}
        actions={actions}
        pipeline={pipeline}
        theme={theme}
        onThemeChange={setTheme}
        onLogout={onLogout}
        user={user}
        onOpenSettings={openSettings}
      >
        {body}
      </Shell>

      <Dialog
        open={!!backTarget}
        onClose={() => setBackTarget(null)}
        title="Go back to Label?"
        description="Changing labels invalidates the distilled ruleset."
        icon={<Icon name="alert" size={19} />}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setBackTarget(null)}>
              Stay here
            </Button>
            <Button variant="primary" size="sm" onClick={confirmStepBack}>
              Go back to Label
            </Button>
          </>
        }
      >
        Your existing labels are kept, but Distill and Verify will run again before
        signals can route. Exchange and execution settings are unaffected.
      </Dialog>

      {toast && (
        <ToastStack>
          <Toast
            tone={toast.tone}
            title={toast.title}
            time={toast.time}
            onClose={clearToast}
          >
            {toast.msg}
          </Toast>
        </ToastStack>
      )}
    </>
  )
}

export default ProductApp
