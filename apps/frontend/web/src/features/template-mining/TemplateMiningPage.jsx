import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Loader } from '@verasig/design-system'
import { MiningMetrics } from './MiningMetrics.jsx'
import { MineView } from './MineView.jsx'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'
import { TemplateExamplesDialog } from './TemplateExamplesDialog.jsx'
import { OverlayManager } from './OverlayManager.jsx'
import { AuditReview } from './AuditReview.jsx'
import { describeAcceptedTemplates } from './templateLabel.js'
import { formatPercent } from './format.js'
import './template-mining.css'

/* Verasig — Parser-first Template Mining.
   Mine, Review and Verify are top-level pipeline steps driven by the `step` prop
   and the shared top-level stepper. Mining and the Verify audit both run
   server-side: MineView streams the mine job, and the audit is fetched fresh
   from the backend (onLoadAudit) whenever the accepted-template set changes.
   This component owns the shared mining state (result, decisions, fetched
   audit) and renders the view for the current step; advancing calls up to the
   parent. Reopening a verified feed lands on Verify: the page loads the latest
   current review and reseeds accepted templates from the backend
   (onLoadConfirmed), so the audit repopulates without changing its input. */

const EMPTY_AUDIT = {
  parsedSignals: [],
  ambiguousCandidates: [],
  rejectedCandidates: [],
  rareTemplates: [],
  potentialMisses: []
}

// A request per keystroke/toggle would hammer the backend; the audit is only
// ever read a moment after the operator settles on a decision.
const AUDIT_DEBOUNCE_MS = 300
const STALE_REVIEW_MESSAGE =
  'Messages or parser settings changed after this review. Re-mine before auditing or confirming.'

function isStaleReview(error) {
  return error?.status === 409 && error?.code === 'MINING_REVIEW_STALE'
}

function TemplateSection({ title, subtitle, groups, action, cardProps }) {
  if (groups.length === 0) return null
  return (
    <section className="vrs-tm-section">
      <div className="vrs-tm-section__head">
        <div>
          <div className="vrs-tm-section__title">{title}</div>
          {subtitle && <div className="vrs-tm-section__sub">{subtitle}</div>}
        </div>
        {action}
      </div>
      <div className="vrs-tm-grid">
        {groups.map((group) => (
          <TemplateGroupCard
            key={group.templateKey}
            group={group}
            {...cardProps(group)}
          />
        ))}
      </div>
    </section>
  )
}

export function TemplateMiningPage({
  activeFeed,
  step = 'mine',
  onStartMine,
  onStreamMine,
  onLoadConfirmed,
  onLoadMineResult,
  onLoadAudit,
  fireToast,
  overlay = {},
  onSaveOverlay,
  onMined,
  onContinueToVerify,
  onBackToReview,
  onConfirmVerification,
  plan,
  onUpgrade,
  decisions: controlledDecisions,
  onDecisionsChange
}) {
  const [result, setResult] = useState(null) // { groups, messages }
  const [internalDecisions, setInternalDecisions] = useState({})
  const [examplesFor, setExamplesFor] = useState(null) // open template's key
  const [confirmedKeys, setConfirmedKeys] = useState(null) // null = not fetched / N/A
  const [resumeChecked, setResumeChecked] = useState(false) // cache lookup done?
  const [restoring, setRestoring] = useState(false)
  const [mineError, setMineError] = useState(null) // set when the mine job fails
  const [mineAttempt, setMineAttempt] = useState(0) // bumped to retry (remounts MineView)
  const [audit, setAudit] = useState(null) // fetched server audit, or null before first fetch
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState(null)
  const [confirmationPending, setConfirmationPending] = useState(false)
  const [confirmationError, setConfirmationError] = useState(null)
  const [overlayPending, setOverlayPending] = useState(false)
  const [overlayError, setOverlayError] = useState(null)
  const [reviewStaleMessage, setReviewStaleMessage] = useState(null)
  const seededFeedRef = useRef(null)
  const auditRequestRef = useRef(0)
  const confirmationRef = useRef(null)
  const overlayMutationRef = useRef(null)

  // Controlled-with-fallback: the parent may own decisions; otherwise local.
  const decisions = controlledDecisions ?? internalDecisions
  const setDecisions = onDecisionsChange ?? setInternalDecisions

  // Mining always runs server-side, against a real, authenticated feed.
  const canMine = Boolean(activeFeed?.id && onStartMine)

  const groups = useMemo(() => result?.groups ?? [], [result])

  // One pass sorts every template into its decision bucket, so the grids, the
  // metrics counts and the verify gate all read the same computation.
  const groupsByStatus = useMemo(() => {
    const buckets = { accepted: [], rejected: [], unreviewed: [] }
    for (const group of groups) {
      buckets[decisions[group.templateKey] || 'unreviewed'].push(group)
    }
    return buckets
  }, [groups, decisions])
  const acceptedGroups = groupsByStatus.accepted

  // Sections group by the miner's suggestion, not the live decision, so a
  // template stays put after the operator acts on it.
  const suggestedAcceptGroups = useMemo(
    () => groups.filter((group) => group.suggestedAction === 'accept'),
    [groups]
  )
  const needsReviewGroups = useMemo(
    () => groups.filter((group) => group.suggestedAction !== 'accept'),
    [groups]
  )

  const acceptedTemplateKeys = useMemo(
    () => acceptedGroups.map((group) => group.templateKey).join('|'),
    [acceptedGroups]
  )
  // Display-only: labels the server audit's parserRuleId back to the family
  // that produced it (Template filter + per-row badge in AuditReview).
  const templates = useMemo(
    () => describeAcceptedTemplates(acceptedGroups),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [acceptedTemplateKeys]
  )

  // The Verify audit is server-computed; fetch it whenever the accepted set
  // changes while it's needed (Review's coverage metric, and the Verify
  // screen), debounced so a run of toggles doesn't fire a request each.
  const auditNeeded = (step === 'review' || step === 'verify') && Boolean(result)
  useEffect(() => {
    if (!auditNeeded) return
    if (!acceptedTemplateKeys) {
      setAudit(EMPTY_AUDIT)
      setAuditLoading(false)
      setAuditError(null)
      return
    }
    if (!onLoadAudit || !activeFeed?.id) return
    setAuditLoading(true)
    setAuditError(null)
    const requestId = ++auditRequestRef.current
    const timer = setTimeout(() => {
      onLoadAudit(
        activeFeed.id,
        result.reviewId,
        acceptedGroups.map((group) => group.templateKey)
      )
        .then((data) => {
          if (requestId !== auditRequestRef.current) return
          setAudit(data ?? EMPTY_AUDIT)
        })
        .catch((error) => {
          if (requestId !== auditRequestRef.current) return
          if (isStaleReview(error)) setReviewStaleMessage(STALE_REVIEW_MESSAGE)
          setAuditError(error?.message || 'Try again in a moment.')
        })
        .finally(() => {
          if (requestId === auditRequestRef.current) setAuditLoading(false)
        })
    }, AUDIT_DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditNeeded, acceptedTemplateKeys, activeFeed?.id, onLoadAudit, result?.reviewId])

  const metrics = useMemo(() => {
    if (!result) return null
    const candidates = groups.reduce((sum, group) => sum + group.count, 0)
    const parsedSignals = audit ? audit.parsedSignals.length : 0
    return {
      totalMessages: result.messages.length,
      candidates,
      groups: groups.length,
      accepted: acceptedGroups.length,
      rejected: groupsByStatus.rejected.length,
      review: groupsByStatus.unreviewed.length,
      parsedSignals,
      coverage: candidates > 0 ? formatPercent(parsedSignals / candidates) : '0%'
    }
  }, [result, groups, audit, acceptedGroups, groupsByStatus])

  // Navigation callbacks read through a ref so effects don't refire on the
  // parent re-creating them each render.
  const navRef = useRef({})
  navRef.current = { onMined, onContinueToVerify, onBackToReview }

  // A new feed drops the previous feed's mining so we re-mine from scratch, and
  // clears the resume state so its confirmed templates are re-fetched and reseeded.
  useEffect(() => {
    setResult(null)
    setExamplesFor(null)
    setConfirmedKeys(null)
    setResumeChecked(false)
    setMineError(null)
    setAudit(null)
    setAuditLoading(false)
    setAuditError(null)
    setConfirmationPending(false)
    setConfirmationError(null)
    setOverlayPending(false)
    setOverlayError(null)
    setReviewStaleMessage(null)
    seededFeedRef.current = null
  }, [activeFeed?.id])

  // Advance to Review as soon as mining lands (only while on the Mine screen).
  useEffect(() => {
    if (step === 'mine' && result) navRef.current.onMined?.()
  }, [step, result])

  // Reopening a verified feed lands on Verify: hydrate its latest current review.
  // On a hit we set `result` and skip MineView; a 404 means there is no current
  // review, so the page falls through to a live mine. Once per feed.
  useEffect(() => {
    if (!onLoadMineResult) return
    if (step !== 'verify' || result || resumeChecked) return
    let cancelled = false
    onLoadMineResult(activeFeed.id)
      .then((payload) => {
        if (!cancelled && payload) handleMineDone(payload)
      })
      .catch((error) => {
        if (!cancelled && isStaleReview(error)) {
          setReviewStaleMessage(STALE_REVIEW_MESSAGE)
        }
      })
      .finally(() => {
        if (!cancelled) setResumeChecked(true)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, activeFeed?.id])

  // Reopening a verified feed lands here with no decisions: fetch the accepted
  // template keys the backend persisted, so the fresh mine can be reseeded. Fetched
  // once per feed (confirmedKeys flips off null); fail-open to none on error.
  useEffect(() => {
    if (!onLoadConfirmed) return
    if (step !== 'verify' || confirmedKeys !== null) return
    if (Object.keys(decisions).length > 0) return
    setRestoring(true)
    onLoadConfirmed(activeFeed.id)
      .then((body) => setConfirmedKeys(body?.acceptedTemplateKeys ?? []))
      .catch(() => setConfirmedKeys([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, activeFeed?.id])

  // Once the fresh mine and the confirmed keys are both in, reseed each confirmed
  // key the mine still produces as accepted — once per feed — then release the
  // guard. Nothing to reseed (empty or drifted keys) falls through to the guard.
  useEffect(() => {
    if (!restoring || !result || confirmedKeys === null) return
    if (seededFeedRef.current === activeFeed?.id) return
    const present = new Set(groups.map((group) => group.templateKey))
    const reseeded = {}
    for (const key of confirmedKeys) {
      if (present.has(key)) reseeded[key] = 'accepted'
    }
    setDecisions(reseeded)
    seededFeedRef.current = activeFeed?.id
    setRestoring(false)
  }, [restoring, result, confirmedKeys, groups, activeFeed?.id, setDecisions])

  // Guard: if decisions drop to zero while on Verify, fall back to Review. Held off
  // while restoring so the reseed can land before the empty state would bounce.
  useEffect(() => {
    if (restoring) return
    if (step === 'verify' && result && acceptedGroups.length === 0) {
      navRef.current.onBackToReview?.()
    }
  }, [step, result, acceptedGroups.length, restoring])

  function handleMineDone(mineResult) {
    setMineError(null)
    setResult({
      reviewId: mineResult?.reviewId,
      inputRevision: mineResult?.inputRevision,
      groups: mineResult?.groups ?? [],
      messages: mineResult?.messages ?? []
    })
    setDecisions({})
    setExamplesFor(null)
    setAudit(null)
    setAuditError(null)
    setReviewStaleMessage(null)
  }

  // A failed mine keeps the operator on the loader with an explicit error and a
  // retry, rather than a transient toast that leaves a blank screen behind.
  function handleMineError(error) {
    setMineError(error?.message || 'Try again in a moment.')
    fireToast?.('rejected', 'Mining failed', error?.message || 'Try again in a moment.')
  }

  function retryMine() {
    setMineError(null)
    setMineAttempt((attempt) => attempt + 1)
  }

  function decide(templateKey, status) {
    setDecisions({ ...decisions, [templateKey]: status })
  }

  function resetDecision(templateKey) {
    const next = { ...decisions }
    delete next[templateKey]
    setDecisions(next)
  }

  function applyAllSuggestedAccepts() {
    const next = { ...decisions }
    for (const group of suggestedAcceptGroups) next[group.templateKey] = 'accepted'
    setDecisions(next)
  }

  function goToVerify() {
    if (acceptedGroups.length > 0 && !overlayPending) onContinueToVerify?.()
  }

  function confirmVerification(destination) {
    if (confirmationRef.current || !onConfirmVerification) {
      return confirmationRef.current
    }

    setConfirmationPending(true)
    setConfirmationError(null)
    const command = onConfirmVerification({
      reviewId: result.reviewId,
      acceptedTemplateKeys: acceptedGroups.map((group) => group.templateKey),
      destination
    })
      .catch((error) => {
        if (isStaleReview(error)) setReviewStaleMessage(STALE_REVIEW_MESSAGE)
        setConfirmationError(error?.message || 'Try again in a moment.')
      })
      .finally(() => {
        confirmationRef.current = null
        setConfirmationPending(false)
      })
    confirmationRef.current = command
    return command
  }

  function saveOverlayAndRemine(nextOverlay) {
    if (overlayMutationRef.current || !onSaveOverlay) {
      return overlayMutationRef.current
    }

    setOverlayPending(true)
    setOverlayError(null)
    const mutation = onSaveOverlay(nextOverlay)
      .then(() => {
        auditRequestRef.current += 1
        setResult(null)
        setDecisions({})
        setExamplesFor(null)
        setConfirmedKeys(null)
        setAudit(null)
        setAuditLoading(false)
        setAuditError(null)
        setMineError(null)
      })
      .catch((error) => {
        setOverlayError(error?.message || 'Try again in a moment.')
        throw error
      })
      .finally(() => {
        overlayMutationRef.current = null
        setOverlayPending(false)
      })
    overlayMutationRef.current = mutation
    return mutation
  }

  function remineStaleReview() {
    auditRequestRef.current += 1
    setResult(null)
    setDecisions({})
    setAudit(null)
    setAuditLoading(false)
    setAuditError(null)
    setConfirmationError(null)
    setResumeChecked(true)
    setMineAttempt((attempt) => attempt + 1)
  }

  const cardProps = (group) => ({
    status: decisions[group.templateKey] || 'unreviewed',
    onAccept: () => decide(group.templateKey, 'accepted'),
    onReject: () => decide(group.templateKey, 'rejected'),
    onReset: () => resetDecision(group.templateKey),
    onShowExamples: () => setExamplesFor(group.templateKey)
  })

  const examplesGroup = examplesFor
    ? groups.find((group) => group.templateKey === examplesFor)
    : null

  // Until mining lands there is nothing to review: show the loader (the
  // server mine job, or a wait note while a cache lookup / feed is pending).
  if (!result) {
    // Verify-resume checks the cache first; hold the loader (don't mount MineView)
    // until that lookup resolves, so a cache hit never kicks off a needless scan.
    const awaitingResume =
      Boolean(onLoadMineResult) && step === 'verify' && !resumeChecked
    return (
      <div className="vrs-page vrs-tm">
        {reviewStaleMessage && (
          <div className="vrs-empty vrs-empty--sm" role="alert">
            <div className="vrs-empty__note">{reviewStaleMessage}</div>
          </div>
        )}
        {mineError ? (
          <div className="vrs-empty vrs-empty--sm" role="alert">
            <div className="vrs-empty__note">Mining failed. {mineError}</div>
            <Button variant="primary" size="sm" onClick={retryMine}>
              Try again
            </Button>
          </div>
        ) : awaitingResume ? (
          <Loader variant="dot" size="sm" title="Loading saved results…" />
        ) : canMine ? (
          <MineView
            key={mineAttempt}
            feed={activeFeed}
            onStart={onStartMine}
            onStream={onStreamMine}
            onDone={handleMineDone}
            onError={handleMineError}
          />
        ) : (
          <div className="vrs-empty vrs-empty--sm">
            <div className="vrs-empty__note">Waiting for a connected feed…</div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="vrs-page vrs-tm">
      {reviewStaleMessage && (
        <div className="vrs-empty vrs-empty--sm" role="alert">
          <div className="vrs-empty__note">{reviewStaleMessage}</div>
          <Button variant="primary" size="sm" onClick={remineStaleReview}>
            Re-mine messages
          </Button>
        </div>
      )}
      {step === 'mine' && <Loader variant="dot" size="sm" title="Opening review…" />}

      {step === 'review' && (
        <>
          <MiningMetrics metrics={metrics} variant="slim" />

          {groups.length === 0 ? (
            <div className="vrs-empty vrs-empty--sm">
              <div className="vrs-empty__note">
                No signal candidates found in this source.
              </div>
            </div>
          ) : (
            <>
              <TemplateSection
                title="Suggested accept"
                subtitle="One decision validates or rejects every message in the template."
                groups={suggestedAcceptGroups}
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={overlayPending}
                    onClick={applyAllSuggestedAccepts}
                  >
                    Apply all {suggestedAcceptGroups.length}
                  </Button>
                }
                cardProps={cardProps}
              />
              <TemplateSection
                title="Needs review"
                groups={needsReviewGroups}
                cardProps={cardProps}
              />
            </>
          )}

          <details className="vrs-tm-advanced">
            <summary>Advanced</summary>
            {onSaveOverlay && (
              <OverlayManager
                overlay={overlay}
                onSave={saveOverlayAndRemine}
                pending={overlayPending}
                error={overlayError}
              />
            )}
          </details>

          <div className="vrs-tm-footer">
            <Button
              variant="ghost"
              disabled={overlayPending}
              onClick={() => setDecisions({})}
            >
              Clear decisions
            </Button>
            <div className="vrs-tm-footer__end">
              {acceptedGroups.length === 0 && (
                <span className="vrs-tm-footer__hint">
                  Accept at least one template to continue.
                </span>
              )}
              <Button
                variant="primary"
                disabled={acceptedGroups.length === 0 || overlayPending}
                onClick={goToVerify}
              >
                Continue to verify
              </Button>
            </div>
          </div>
        </>
      )}

      {step === 'verify' && (
        <>
          <Button
            variant="ghost"
            size="sm"
            disabled={confirmationPending}
            onClick={() => onBackToReview?.()}
          >
            Back to review
          </Button>
          <AuditReview
            audit={audit || EMPTY_AUDIT}
            messages={result.messages}
            templates={templates}
            hasAccepted={acceptedGroups.length > 0}
            loading={auditLoading}
            error={auditError}
            confirmationPending={confirmationPending}
            confirmationError={confirmationError}
            plan={plan}
            onUpgrade={onUpgrade}
            onFinish={() => confirmVerification('exchange')}
            onKeepVerified={() => confirmVerification('feeds')}
          />
        </>
      )}

      <TemplateExamplesDialog
        group={examplesGroup}
        open={Boolean(examplesGroup)}
        onClose={() => setExamplesFor(null)}
        status={
          examplesGroup
            ? decisions[examplesGroup.templateKey] || 'unreviewed'
            : 'unreviewed'
        }
        onAccept={() => {
          if (!examplesGroup) return
          decide(examplesGroup.templateKey, 'accepted')
          setExamplesFor(null)
        }}
        onReject={() => {
          if (!examplesGroup) return
          decide(examplesGroup.templateKey, 'rejected')
          setExamplesFor(null)
        }}
        onReset={() => examplesGroup && resetDecision(examplesGroup.templateKey)}
      />
    </div>
  )
}

export default TemplateMiningPage
