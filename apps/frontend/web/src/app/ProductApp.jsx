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
import { FeedsView } from '../features/sources/FeedsView.jsx'
import { SignalsView } from '../features/signals/SignalsView.jsx'
import { BackfillView } from '../features/pipeline/steps/BackfillView.jsx'
import { LabelView } from '../features/pipeline/steps/LabelView.jsx'
import { DistillView } from '../features/pipeline/steps/DistillView.jsx'
import { VerifyView } from '../features/pipeline/steps/VerifyView.jsx'
import { PaidFeaturePlaceholder } from '../features/pipeline/steps/PaidFeaturePlaceholder.jsx'
import { ExchangesView } from '../features/exchanges/ExchangesView.jsx'
import { SettingsView } from '../features/settings/SettingsView.jsx'
import { useWorkflowState } from './workflow/useWorkflowState.js'
import {
  connectTelegram as connectTelegramApi,
  verifyTelegram
} from '../shared/api/telegramApi.js'
import {
  cancelBackfill,
  createFeed,
  deleteFeed,
  startBackfill as startBackfillJob,
  startDeletionRescan,
  streamBackfillProgress,
  streamDeletionRescanProgress
} from '../shared/api/feedsApi.js'
import {
  getLabelCounts,
  getRules,
  getVerifySamples,
  listMessages,
  recordLabel,
  startDistill,
  streamDistillProgress,
  submitVerify
} from '../shared/api/pipelineApi.js'
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

export function deletionRescanToast(feed, result = {}) {
  const signalCount = result.newDeletedSignalCount || 0
  const nonSignalCount = result.newDeletedNonSignalCount || 0
  const gapCount = result.newSuspectedGapCount || 0
  const warningCount = nonSignalCount + gapCount

  if (signalCount > 0) {
    return {
      tone: 'rejected',
      title: 'Signal deletion confirmed',
      msg: `${feed.name} has ${signalCount} deleted signal message${signalCount === 1 ? '' : 's'}.`
    }
  }

  if (warningCount > 0) {
    return {
      tone: 'pending',
      title: 'Deleted messages found',
      msg: `${feed.name} has ${warningCount} newly detected deleted or missing message${warningCount === 1 ? '' : 's'} that are not signals.`
    }
  }

  return {
    tone: 'verified',
    title: 'No deleted messages found',
    msg: `${feed.name} has no newly detected deleted messages.`
  }
}

export function ProductApp({ authToken, user: sessionUser, onLogout }) {
  const [theme, setTheme] = useTheme()

  const [user, setUser] = useState(() => mergeUserDefaults(sessionUser))
  const [checkingGapFeedId, setCheckingGapFeedId] = useState(null)

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
    feeds,
    activeFeed,
    verifyAttempt,
    setVerifyAttempt,
    setScreen,
    bybitConnected,
    toast,
    clearToast,
    fireToast,
    backTarget,
    signalsPreset,
    backfillMode,
    isWorkflow,
    pipelineStep,
    goToDeletedSignals,
    startBackfill,
    retryBackfill,
    resumeFeed,
    fetchNewMessages,
    refetchFullHistory,
    reviewLabels,
    removeFeed,
    checkGaps: previewCheckGaps,
    stopAfterVerify,
    routeAfterVerify,
    backtestFeed,
    onBackfillComplete,
    onBackfillCancel,
    onBackfillError,
    requestStepBack,
    confirmStepBack,
    openSettings,
    restoreNav,
    handleNav,
    exitToFeeds,
    exitToSources,
    connectBybit,
    disconnectBybit,
    connectTelegram: markTelegramConnected,
    refreshSources,
    upsertFeed,
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

  async function addTelegramFeed(tag) {
    const feed = await createFeed(authToken, tag)
    upsertFeed(feed)
    fireToast('verified', 'Feed added', `${feed.name} is ready to backfill.`)
  }

  async function handleRemoveFeed(feed) {
    try {
      await deleteFeed(authToken, feed.id)
      removeFeed(feed.id)
      fireToast('info', 'Feed removed', `${feed.name} was removed from your feeds.`)
    } catch (error) {
      fireToast(
        'rejected',
        'Could not remove feed',
        error?.message || 'Try again in a moment.'
      )
    }
  }

  function showDeletionRescanToast(feed, result = {}) {
    const notice = deletionRescanToast(feed, result)
    fireToast(notice.tone, notice.title, notice.msg)
  }

  async function handleCheckGaps(feed) {
    if (!authToken) {
      previewCheckGaps(feed)
      return
    }

    setCheckingGapFeedId(feed.id)

    try {
      await startDeletionRescan(authToken, feed.id)
      streamDeletionRescanProgress(authToken, feed.id, {
        onDone: (result) => {
          setCheckingGapFeedId(null)
          void refreshSources().catch(() => {})
          showDeletionRescanToast(feed, result)
        },
        onError: (error) => {
          setCheckingGapFeedId(null)
          fireToast(
            'rejected',
            'Check gaps failed',
            error?.message || 'Could not check this feed right now.'
          )
        }
      })
    } catch (error) {
      setCheckingGapFeedId(null)
      fireToast(
        'rejected',
        'Check gaps failed',
        error?.message || 'Could not check this feed right now.'
      )
    }
  }

  function completeBackfill(result) {
    onBackfillComplete(result)
    void refreshSources().catch(() => {})
  }

  function handleBackfillError(error) {
    void refreshSources().catch(() => {})
    if (error?.status === 'cancelled') return
    onBackfillError(error)
  }

  if (nav === 'signals') {
    title = 'Signals'
    subtitle = 'Signals extracted from your verified feeds'
    body = (
      <SignalsView
        authToken={authToken}
        feeds={feeds}
        initial={signalsPreset}
        onGoToSources={() => {
          setNav('sources')
          setScreen(telegramConnected ? 'feeds' : 'sources')
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
        feeds={feeds}
        onConnectTelegram={() => setScreen('tg-setup')}
        onOpenTelegram={() => setScreen('feeds')}
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
  } else if (screen === 'feeds') {
    title = 'Telegram'
    subtitle = `${feeds.length} feeds · ${feeds.filter((c) => c.status === 'analyzed').length} analyzed`
    breadcrumb = 'Sources'
    onExit = exitToSources
    body = (
      <FeedsView
        feeds={feeds}
        onStartBackfill={startBackfill}
        onRetry={retryBackfill}
        onResume={resumeFeed}
        onFetchNew={fetchNewMessages}
        onRefetchFull={refetchFullHistory}
        onReviewLabels={reviewLabels}
        onRemove={handleRemoveFeed}
        onViewDeleted={goToDeletedSignals}
        onCheckGaps={handleCheckGaps}
        checkingGapFeedId={checkingGapFeedId}
        onBacktest={backtestFeed}
        onAddFeed={addTelegramFeed}
      />
    )
  } else if (isWorkflow && activeFeed) {
    breadcrumb = activeFeed.name
    onExit = exitToFeeds
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
    subtitle = `${activeFeed.name} · ${stepTitles[screen][1]}`

    if (screen === 'backfill') {
      body = (
        <BackfillView
          chat={activeFeed}
          onStart={(chatId) => startBackfillJob(authToken, chatId, backfillMode)}
          onStream={(chatId, handlers) =>
            streamBackfillProgress(authToken, chatId, handlers)
          }
          onCancelBackfill={(chatId) => cancelBackfill(authToken, chatId)}
          onCancel={onBackfillCancel}
          onComplete={completeBackfill}
          onError={handleBackfillError}
        />
      )
    } else if (screen === 'label') {
      body = (
        <LabelView
          chatId={activeFeed.id}
          onListMessages={(chatId) => listMessages(authToken, chatId)}
          onGetCounts={(chatId) => getLabelCounts(authToken, chatId)}
          onRecordLabel={(chatId, msgId, label) =>
            recordLabel(authToken, chatId, msgId, label)
          }
          onDistill={() => setScreen('distill')}
          onError={(tone, title, msg) => fireToast(tone, title, msg)}
          key={`label-${verifyAttempt}`}
        />
      )
    } else if (screen === 'distill') {
      body = (
        <DistillView
          chatId={activeFeed.id}
          onStartDistill={(chatId) => startDistill(authToken, chatId)}
          onStreamProgress={(chatId, handlers) =>
            streamDistillProgress(authToken, chatId, handlers)
          }
          onGetRules={(chatId) => getRules(authToken, chatId)}
          onComplete={() => setScreen('verify')}
          onError={(tone, title, msg) => fireToast(tone, title, msg)}
        />
      )
    } else if (screen === 'verify') {
      body = (
        <VerifyView
          key={`verify-${verifyAttempt}`}
          chatId={activeFeed.id}
          onGetSamples={(chatId) => getVerifySamples(authToken, chatId)}
          onSubmit={(chatId, verdicts) => submitVerify(authToken, chatId, verdicts)}
          onPass={routeAfterVerify}
          onStop={() => {
            stopAfterVerify()
            void refreshSources().catch(() => {})
          }}
          onLoop={() => {
            setVerifyAttempt((a) => a + 1)
            setScreen('label')
            fireToast(
              'pending',
              'Refining rules',
              "Label a few more, then we'll re-verify."
            )
          }}
          onError={(tone, title, msg) => fireToast(tone, title, msg)}
        />
      )
    } else if (
      screen === 'exchange' ||
      screen === 'risk' ||
      screen === 'backtest' ||
      screen === 'backtest-result'
    ) {
      const featureName =
        screen === 'exchange'
          ? 'Exchange routing'
          : screen === 'risk'
            ? 'Execution'
            : 'Backtesting'
      title = featureName
      subtitle = `${activeFeed.name} · Available on a higher plan`
      body = (
        <PaidFeaturePlaceholder
          feature={featureName}
          onDone={() => {
            void refreshSources().catch(() => {})
            exitToFeeds()
          }}
        />
      )
    }
  } else {
    title = 'Sources'
    body = (
      <SourcesView
        telegramConnected={telegramConnected}
        feeds={feeds}
        onConnectTelegram={() => setScreen('tg-setup')}
        onOpenTelegram={() => setScreen('feeds')}
      />
    )
  }

  if (nav === 'sources' && screen === 'feeds') {
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
