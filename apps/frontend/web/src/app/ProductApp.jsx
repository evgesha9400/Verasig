import { useState, useEffect } from 'react'
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
import { PaidFeaturePlaceholder } from '../features/pipeline/steps/PaidFeaturePlaceholder.jsx'
import { ExchangesView } from '../features/exchanges/ExchangesView.jsx'
import { TemplateMiningPage } from '../features/template-mining/TemplateMiningPage.jsx'
import { SettingsView } from '../features/settings/SettingsView.jsx'
import { useWorkflowState } from './workflow/useWorkflowState.js'
import { isStepLocked } from '../domain/workflow/stepAccess.js'
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
  getParserOverlay,
  putParserOverlay,
  listFeedHistory
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
  const [rescanScanned, setRescanScanned] = useState(null)

  useEffect(() => {
    setUser(mergeUserDefaults(sessionUser))
  }, [sessionUser])

  function updateUser(patch) {
    setUser((current) => {
      return { ...current, ...patch }
    })
  }

  const [overlay, setOverlay] = useState({})

  useEffect(() => {
    if (!authToken) return
    getParserOverlay(authToken)
      .then((body) => setOverlay(body.overlay || {}))
      .catch(() => {})
  }, [authToken])

  async function saveOverlay(next) {
    try {
      const body = await putParserOverlay(authToken, next)
      setOverlay(body.overlay || next)
    } catch (error) {
      fireToast(
        'rejected',
        'Could not save',
        error?.message || 'Try again in a moment.'
      )
    }
  }

  const {
    nav,
    setNav,
    screen,
    telegramConnected,
    feeds,
    activeFeed,
    setScreen,
    bybitConnected,
    toast,
    clearToast,
    fireToast,
    backTarget,
    signalsPreset,
    backfillMode,
    backfillDepth,
    isWorkflow,
    pipelineStep,
    goToDeletedSignals,
    openFeed,
    fetchNewMessages,
    refetchFullHistory,
    reopenMining,
    removeFeed,
    checkGaps: previewCheckGaps,
    stopAfterVerify,
    routeAfterVerify,
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
  } = useWorkflowState(authToken, user.plan)

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-density', 'regular')
    root.setAttribute('data-wide', 'center')
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
    setRescanScanned(null)

    try {
      await startDeletionRescan(authToken, feed.id)
      streamDeletionRescanProgress(authToken, feed.id, {
        onProgress: (progress) => {
          if (progress.scanned != null) setRescanScanned(progress.scanned)
        },
        onDone: (result) => {
          setCheckingGapFeedId(null)
          setRescanScanned(null)
          void refreshSources().catch(() => {})
          showDeletionRescanToast(feed, result)
        },
        onError: (error) => {
          setCheckingGapFeedId(null)
          setRescanScanned(null)
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
        onOpenFeed={openFeed}
        onFetchNew={fetchNewMessages}
        onRefetchFull={refetchFullHistory}
        onReviewTemplates={reopenMining}
        onRemove={handleRemoveFeed}
        onViewDeleted={goToDeletedSignals}
        onCheckGaps={handleCheckGaps}
        checkingGapFeedId={checkingGapFeedId}
        rescanScanned={rescanScanned}
        onAddFeed={addTelegramFeed}
      />
    )
  } else if (isWorkflow && activeFeed) {
    breadcrumb = activeFeed.name
    onExit = exitToFeeds
    pipeline = (
      <Pipeline
        current={pipelineStep}
        plan={user.plan}
        onStepBack={requestStepBack}
      />
    )

    const stepTitles = {
      backfill: ['Backfill', 'Pulling message history'],
      mine: ['Mine', 'Discovering signal formats'],
      review: ['Review', 'Accept the real signal templates'],
      verify: ['Verify', 'Audit the full history, then confirm'],
      exchange: ['Exchange', 'Route verified signals'],
      backtest: ['Backtest', 'Simulating performance'],
      execution: ['Execution', 'Size, entry and exit for every verified signal'],
      'backtest-result': ['Signal quality', 'Backtest results']
    }

    title = stepTitles[screen][0]
    subtitle = `${activeFeed.name} · ${stepTitles[screen][1]}`

    if (screen === 'backfill') {
      body = (
        <BackfillView
          feed={activeFeed}
          mode={backfillMode}
          onStart={(chatId) =>
            startBackfillJob(authToken, chatId, backfillMode, backfillDepth)
          }
          onStream={(chatId, handlers) =>
            streamBackfillProgress(authToken, chatId, handlers)
          }
          onCancelBackfill={(chatId) => cancelBackfill(authToken, chatId)}
          onCancel={onBackfillCancel}
          onComplete={completeBackfill}
          onError={handleBackfillError}
        />
      )
    } else if (screen === 'mine' || screen === 'review' || screen === 'verify') {
      body = (
        <TemplateMiningPage
          activeFeed={activeFeed}
          authToken={authToken}
          step={screen}
          onListMessages={(chatId) => listFeedHistory(authToken, chatId)}
          fireToast={fireToast}
          overlay={overlay}
          onSaveOverlay={saveOverlay}
          onMined={() => setScreen('review')}
          onContinueToVerify={() => setScreen('verify')}
          onBackToReview={() => setScreen('review')}
          onFinish={routeAfterVerify}
          onKeepVerified={() => {
            stopAfterVerify()
            void refreshSources().catch(() => {})
          }}
        />
      )
    } else if (
      screen === 'exchange' ||
      screen === 'backtest' ||
      screen === 'execution' ||
      screen === 'backtest-result'
    ) {
      // These steps aren't built yet. Message depends on why they're blocked:
      // beyond the plan's reach (upgrade) vs. reachable-but-unbuilt (coming soon).
      const lockedByPlan = isStepLocked(pipelineStep, user.plan)
      const featureName =
        screen === 'exchange'
          ? 'Exchange routing'
          : screen === 'execution'
            ? 'Execution'
            : 'Backtesting'
      title = featureName
      subtitle = lockedByPlan
        ? `${activeFeed.name} · Available on a higher plan`
        : `${activeFeed.name} · Coming soon`
      body = (
        <PaidFeaturePlaceholder
          feature={featureName}
          lockedByPlan={lockedByPlan}
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
        title="Go back to Mining?"
        description="Revisiting Mining means the compiled ruleset may change."
        icon={<Icon name="alert" size={19} />}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setBackTarget(null)}>
              Stay here
            </Button>
            <Button variant="primary" size="sm" onClick={confirmStepBack}>
              Go back to Mining
            </Button>
          </>
        }
      >
        Your family decisions are kept, but the compiled rules and audit will refresh.
        Exchange and execution settings are unaffected.
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
