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
import { CompiledRulesPanel } from './CompiledRulesPanel.jsx'
import { OverlayManager } from './OverlayManager.jsx'
import { AuditReview } from './AuditReview.jsx'
import { formatPercent } from './format.js'
import { toggleInSet } from './toggleSet.js'
import './template-mining.css'

/* Verasig — Parser-first Template Mining (pipeline wizard step).
   Runs the deterministic, local pipeline against the active feed on entry: load
   history → mine families → review format families → compile rules → audit the
   full history. All business logic lives in domain/template-mining; this
   component only holds UI state. Rules and audit recompute reactively from the
   decisions state, so revisiting the step is safe with no remount. */

const STAGES = [
  { id: 'mine', label: 'Mine' },
  { id: 'review', label: 'Review' },
  { id: 'confirm', label: 'Confirm' }
]

function parsePasted(text) {
  return text
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter((block) => block.length > 0)
    .map((block, index) => ({ id: `paste-${index + 1}`, text: block }))
}

// Sample and paste are static, local arrays; the feed source is loaded
// separately (real stored messages when authenticated, demo seed offline).
function resolveStaticMessages(source, pasted) {
  if (source === 'sample') return SAMPLE_MESSAGES
  if (source === 'paste') return parsePasted(pasted)
  return []
}

function StageIndicator({ activeId }) {
  const activeIndex = STAGES.findIndex((stage) => stage.id === activeId)
  return (
    <div className="vrs-tm-stages">
      {STAGES.map((stage, index) => (
        <span
          key={stage.id}
          className={`vrs-tm-stage ${index === activeIndex ? 'is-active' : ''} ${
            index < activeIndex ? 'is-done' : ''
          }`}
        >
          {stage.label}
        </span>
      ))}
    </div>
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
  onKeepVerified
}) {
  const [source, setSource] = useState('sample')
  const [pasted, setPasted] = useState('')
  const [result, setResult] = useState(null) // { groups, messages }
  const [decisions, setDecisions] = useState({}) // templateKey -> 'accepted' | 'rejected'
  const [expanded, setExpanded] = useState(() => new Set())
  const [running, setRunning] = useState(true)

  const messages = useMemo(
    () => resolveStaticMessages(source, pasted),
    [source, pasted]
  )
  const pastedCount = useMemo(() => parsePasted(pasted).length, [pasted])

  const groups = useMemo(() => result?.groups ?? [], [result])

  // One pass over groups sorts every family into its decision bucket, so the
  // family grid, the metrics counts and the audit gate all read off the same
  // computation instead of each re-filtering groups by status separately.
  const groupsByStatus = useMemo(() => {
    const buckets = { accepted: [], rejected: [], unreviewed: [] }
    for (const group of groups) {
      buckets[decisions[group.templateKey] || 'unreviewed'].push(group)
    }
    return buckets
  }, [groups, decisions])
  const acceptedGroups = groupsByStatus.accepted

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
      `${mined.length} format families from ${minedMessages.length} messages.`
    )
  }

  // The auto-run effect reads mining callbacks through a ref so a parent
  // re-render handing down fresh closures never restarts it (and never re-mines,
  // which would drop the reviewer's decisions).
  const runRef = useRef({ finishMining, fireToast, onListMessages, authToken })
  runRef.current = { finishMining, fireToast, onListMessages, authToken }

  // The feed source loads the full backfilled history for the connected feed
  // (GET /feeds/{id}/messages/history — every message); offline it falls back to
  // the bundled demo history so the prototype still runs. Auto-runs on entry and
  // whenever the active feed changes — no button click in the primary path.
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

  function runStaticMining() {
    finishMining(messages)
  }

  function decide(templateKey, status) {
    setDecisions((current) => ({ ...current, [templateKey]: status }))
  }

  function resetDecision(templateKey) {
    setDecisions((current) => {
      const next = { ...current }
      delete next[templateKey]
      return next
    })
  }

  function applySuggestions() {
    const next = {}
    for (const group of groups) {
      if (group.suggestedAction === 'accept') next[group.templateKey] = 'accepted'
      else if (group.suggestedAction === 'reject') next[group.templateKey] = 'rejected'
    }
    setDecisions(next)
  }

  function toggleExamples(templateKey) {
    setExpanded((current) => toggleInSet(current, templateKey))
  }

  const activeStage =
    running || !result ? 'mine' : acceptedGroups.length > 0 ? 'confirm' : 'review'

  return (
    <div className="vrs-page vrs-tm">
      <StageIndicator activeId={activeStage} />

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

      {running && !result ? (
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">Mining the connected feed…</div>
        </div>
      ) : !result ? (
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">
            No messages to mine yet — connect and backfill a feed first.
          </div>
        </div>
      ) : (
        <>
          <MiningMetrics metrics={metrics} />

          <section className="vrs-tm-section">
            <div className="vrs-tm-section__head">
              <div>
                <div className="vrs-tm-section__title">Template families</div>
                <div className="vrs-tm-section__sub">
                  Review format families, not individual messages — one decision
                  validates or rejects every message in the family.
                </div>
              </div>
              <div className="vrs-tm-bulk">
                <Button variant="secondary" size="sm" onClick={applySuggestions}>
                  Apply suggestions
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDecisions({})}>
                  Clear decisions
                </Button>
              </div>
            </div>

            {groups.length === 0 ? (
              <div className="vrs-empty vrs-empty--sm">
                <div className="vrs-empty__note">
                  No signal candidates found in this source.
                </div>
              </div>
            ) : (
              <div className="vrs-tm-grid">
                {groups.map((group) => (
                  <TemplateGroupCard
                    key={group.templateKey}
                    group={group}
                    status={decisions[group.templateKey] || 'unreviewed'}
                    expanded={expanded.has(group.templateKey)}
                    onAccept={() => decide(group.templateKey, 'accepted')}
                    onReject={() => decide(group.templateKey, 'rejected')}
                    onReset={() => resetDecision(group.templateKey)}
                    onToggleExamples={() => toggleExamples(group.templateKey)}
                  />
                ))}
              </div>
            )}
          </section>

          <CompiledRulesPanel rules={rules} />

          {onSaveOverlay && <OverlayManager overlay={overlay} onSave={onSaveOverlay} />}

          <AuditReview
            audit={
              audit || {
                parsedSignals: [],
                ambiguousCandidates: [],
                rejectedCandidates: [],
                rareTemplates: [],
                potentialMisses: []
              }
            }
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
