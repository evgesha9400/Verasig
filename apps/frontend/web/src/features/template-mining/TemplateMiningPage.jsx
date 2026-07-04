import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@verasig/design-system'
import {
  SAMPLE_MESSAGES,
  FEED_MESSAGES,
  toChatMessages,
  mineTemplateGroups,
  compileRuleFromTemplate,
  applyAcceptedRules
} from '../../domain/template-mining/index.js'
import { MiningSourcePanel } from './MiningSourcePanel.jsx'
import { MiningMetrics } from './MiningMetrics.jsx'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'
import { TemplateExamplesDialog } from './TemplateExamplesDialog.jsx'
import { OverlayManager } from './OverlayManager.jsx'
import { AuditReview } from './AuditReview.jsx'
import { formatPercent } from './format.js'
import './template-mining.css'

/* Verasig — Parser-first Template Mining.
   Mine, Review and Verify are now top-level pipeline steps: the active one is
   driven by the `step` prop and the shared top-level stepper, not an internal
   sub-stepper. This component owns the shared mining state (result, decisions)
   and renders the view for the current step; advancing calls up to the parent
   to change the screen. Rules and audit recompute reactively from decisions, so
   revisiting Review/Verify is safe. */

const EMPTY_AUDIT = {
  parsedSignals: [],
  ambiguousCandidates: [],
  rejectedCandidates: [],
  rareTemplates: [],
  potentialMisses: []
}

function parsePasted(text) {
  return text
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter((block) => block.length > 0)
    .map((block, index) => ({ id: `paste-${index + 1}`, text: block }))
}

function resolveStaticMessages(source, pasted) {
  if (source === 'sample') return SAMPLE_MESSAGES
  if (source === 'paste') return parsePasted(pasted)
  return []
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
  authToken,
  step = 'mine',
  onListMessages,
  fireToast,
  overlay = {},
  onSaveOverlay,
  onMined,
  onContinueToVerify,
  onBackToReview,
  onFinish,
  onKeepVerified,
  decisions: controlledDecisions,
  onDecisionsChange
}) {
  const [source, setSource] = useState('sample')
  const [pasted, setPasted] = useState('')
  const [result, setResult] = useState(null) // { groups, messages }
  const [internalDecisions, setInternalDecisions] = useState({})
  const [examplesFor, setExamplesFor] = useState(null) // open template's key
  const [running, setRunning] = useState(true)

  // Controlled-with-fallback: the parent may own decisions (so they survive this
  // component unmounting on a screen change); otherwise we keep them locally.
  const decisions = controlledDecisions ?? internalDecisions
  const setDecisions = onDecisionsChange ?? setInternalDecisions

  const messages = useMemo(
    () => resolveStaticMessages(source, pasted),
    [source, pasted]
  )
  const pastedCount = useMemo(() => parsePasted(pasted).length, [pasted])
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
  const rules = useMemo(
    () => acceptedGroups.map((group) => compileRuleFromTemplate(group, overlay)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [acceptedTemplateKeys, overlay]
  )

  const audit = useMemo(() => {
    if (!result || rules.length === 0) return null
    return applyAcceptedRules(result.messages, rules, overlay)
  }, [result, rules, overlay])

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

  function finishMining(minedMessages) {
    if (!minedMessages || minedMessages.length === 0) {
      fireToast?.('pending', 'Nothing to mine', 'This source has no messages yet.')
      return
    }
    const mined = mineTemplateGroups(minedMessages, overlay)
    setResult({ groups: mined, messages: minedMessages })
    setDecisions({})
    setExamplesFor(null)
    fireToast?.(
      'verified',
      'Template mining complete',
      `${mined.length} templates from ${minedMessages.length} messages.`
    )
  }

  const runRef = useRef({ finishMining, fireToast, onListMessages, authToken })
  runRef.current = { finishMining, fireToast, onListMessages, authToken }

  // Navigation callbacks read through a ref so effects don't refire on the
  // parent re-creating them each render.
  const navRef = useRef({})
  navRef.current = { onMined, onContinueToVerify, onBackToReview }

  // Auto-runs on entry and whenever the active feed changes — no button click in
  // the primary path. Loads the full backfilled history when authenticated, else
  // the bundled demo history so the prototype still runs.
  useEffect(() => {
    const feedId = activeFeed?.id ?? null
    const {
      finishMining: mine,
      fireToast: toast,
      onListMessages: list,
      authToken: token
    } = runRef.current

    if (!(token && list && feedId)) {
      setRunning(true)
      mine(FEED_MESSAGES)
      setRunning(false)
      return undefined
    }

    let active = true
    setRunning(true)
    Promise.resolve(list(feedId))
      .then((response) => {
        if (active) mine(toChatMessages(response.messages || []))
      })
      .catch((error) => {
        if (active)
          toast?.(
            'rejected',
            'Could not load feed messages',
            error?.message || 'Try again in a moment.'
          )
      })
      .finally(() => {
        if (active) setRunning(false)
      })
    return () => {
      active = false
    }
    // Keyed on the active feed only; callbacks are read through runRef so an
    // overlay or callback identity change never re-mines and drops decisions.
  }, [activeFeed?.id])

  // Advance to Review as soon as mining lands (only while on the Mine screen).
  useEffect(() => {
    if (step === 'mine' && result && !running) navRef.current.onMined?.()
  }, [step, result, running])

  // Guard: if decisions drop to zero while on Verify, fall back to Review.
  useEffect(() => {
    if (step === 'verify' && result && acceptedGroups.length === 0) {
      navRef.current.onBackToReview?.()
    }
  }, [step, result, acceptedGroups.length])

  function runStaticMining() {
    finishMining(messages)
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
    if (acceptedGroups.length > 0) onContinueToVerify?.()
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

  const showMineLoader = step === 'mine' || !result

  return (
    <div className="vrs-page vrs-tm">
      {showMineLoader && (
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">
            {running
              ? 'Mining the connected feed…'
              : result
                ? 'Opening review…'
                : 'No messages to mine yet — connect and backfill a feed first.'}
          </div>
        </div>
      )}

      {step === 'review' && result && (
        <>
          <details className="vrs-tm-altsource">
            <summary>Use sample or pasted messages instead</summary>
            <MiningSourcePanel
              source={source}
              onSourceChange={setSource}
              pasted={pasted}
              onPastedChange={setPasted}
              feeds={[]}
              feedId={null}
              onFeedChange={() => {}}
              selectedFeedName={activeFeed?.name}
              authenticated={Boolean(authToken)}
              demoFeedCount={FEED_MESSAGES.length}
              sampleCount={SAMPLE_MESSAGES.length}
              pastedCount={pastedCount}
              running={running}
              canRun={messages.length > 0}
              onRun={runStaticMining}
            />
          </details>

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
              <OverlayManager overlay={overlay} onSave={onSaveOverlay} />
            )}
          </details>

          <div className="vrs-tm-footer">
            <Button variant="ghost" onClick={() => setDecisions({})}>
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
                disabled={acceptedGroups.length === 0}
                onClick={goToVerify}
              >
                Continue to verify
              </Button>
            </div>
          </div>
        </>
      )}

      {step === 'verify' && result && (
        <>
          <Button variant="ghost" size="sm" onClick={() => onBackToReview?.()}>
            Back to review
          </Button>
          <AuditReview
            audit={audit || EMPTY_AUDIT}
            messages={result.messages}
            rules={rules}
            hasAccepted={acceptedGroups.length > 0}
            onFinish={onFinish}
            onKeepVerified={onKeepVerified}
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
        onAccept={() => examplesGroup && decide(examplesGroup.templateKey, 'accepted')}
        onReject={() => examplesGroup && decide(examplesGroup.templateKey, 'rejected')}
        onReset={() => examplesGroup && resetDecision(examplesGroup.templateKey)}
      />
    </div>
  )
}

export default TemplateMiningPage
