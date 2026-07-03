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
import { MiningStepBar } from './MiningStepBar.jsx'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'
import { OverlayManager } from './OverlayManager.jsx'
import { AuditReview } from './AuditReview.jsx'
import { formatPercent } from './format.js'
import { toggleInSet } from './toggleSet.js'
import './template-mining.css'

/* Verasig — Parser-first Template Mining (pipeline wizard step).
   Three sub-steps shown one at a time: Mine (auto-runs the deterministic local
   pipeline against the active feed) → Review (accept/reject templates) → Verify
   (audit the full history, then confirm). All business logic lives in
   domain/template-mining; this component only holds UI state. Rules and audit
   recompute reactively from the decisions state, so revisiting is safe. */

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
  onListMessages,
  fireToast,
  overlay = {},
  onSaveOverlay,
  onFinish,
  onKeepVerified,
  decisions: controlledDecisions,
  onDecisionsChange
}) {
  const [source, setSource] = useState('sample')
  const [pasted, setPasted] = useState('')
  const [result, setResult] = useState(null) // { groups, messages }
  const [internalDecisions, setInternalDecisions] = useState({})
  const [expanded, setExpanded] = useState(() => new Set())
  const [running, setRunning] = useState(true)
  const [subStep, setSubStep] = useState('mine') // 'mine' | 'review' | 'verify'

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
    setExpanded(new Set())
    fireToast?.(
      'verified',
      'Template mining complete',
      `${mined.length} templates from ${minedMessages.length} messages.`
    )
  }

  const runRef = useRef({ finishMining, fireToast, onListMessages, authToken })
  runRef.current = { finishMining, fireToast, onListMessages, authToken }

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
    setSubStep('mine')

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

  // Advance to Review as soon as mining lands; a re-mine resets to Mine above.
  useEffect(() => {
    if (subStep === 'mine' && result && !running) setSubStep('review')
  }, [subStep, result, running])

  // Guard: if decisions drop to zero while on Verify, fall back to Review.
  useEffect(() => {
    if (subStep === 'verify' && acceptedGroups.length === 0) setSubStep('review')
  }, [subStep, acceptedGroups.length])

  function runStaticMining() {
    setSubStep('mine')
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

  function toggleExamples(templateKey) {
    setExpanded((current) => toggleInSet(current, templateKey))
  }

  function goToVerify() {
    if (acceptedGroups.length > 0) setSubStep('verify')
  }

  const cardProps = (group) => ({
    status: decisions[group.templateKey] || 'unreviewed',
    expanded: expanded.has(group.templateKey),
    onAccept: () => decide(group.templateKey, 'accepted'),
    onReject: () => decide(group.templateKey, 'rejected'),
    onReset: () => resetDecision(group.templateKey),
    onToggleExamples: () => toggleExamples(group.templateKey)
  })

  return (
    <div className="vrs-page vrs-tm">
      <MiningStepBar
        active={subStep}
        canVerify={acceptedGroups.length > 0}
        onNavigate={setSubStep}
      />

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

      {subStep === 'mine' && (
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

      {subStep === 'review' && result && (
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

      {subStep === 'verify' && result && (
        <>
          <Button variant="ghost" size="sm" onClick={() => setSubStep('review')}>
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
    </div>
  )
}

export default TemplateMiningPage
