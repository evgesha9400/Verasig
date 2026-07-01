import { useMemo, useState } from 'react'
import { Button } from '@verasig/design-system'
import {
  SAMPLE_MESSAGES,
  FEED_MESSAGES,
  toChatMessages,
  mineTemplateGroups,
  compileRuleFromTemplate,
  applyAcceptedRules
} from '../../domain/template-mining/index.js'
import { MiningPipelineRibbon } from './MiningPipelineRibbon.jsx'
import { MiningSourcePanel } from './MiningSourcePanel.jsx'
import { MiningMetrics } from './MiningMetrics.jsx'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'
import { CompiledRulesPanel } from './CompiledRulesPanel.jsx'
import { OverlayManager } from './OverlayManager.jsx'
import { AuditReview } from './AuditReview.jsx'
import { formatPercent } from './format.js'
import './templateMining.css'

/* Verasig — Parser-first Template Mining (prototype page).
   Orchestrates the deterministic, local pipeline: load history → mine families →
   review format families → compile rules → audit the full history. All business
   logic lives in domain/template-mining; this component only holds UI state. */

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

export function TemplateMiningPage({
  feeds = [],
  authToken,
  onListMessages,
  fireToast,
  overlay = {},
  onSaveOverlay
}) {
  const [source, setSource] = useState('feed')
  const [pasted, setPasted] = useState('')
  const [feedId, setFeedId] = useState(null)
  const [result, setResult] = useState(null) // { groups, messages }
  const [decisions, setDecisions] = useState({}) // templateKey -> 'accepted' | 'rejected'
  const [expanded, setExpanded] = useState(() => new Set())
  const [running, setRunning] = useState(false)

  const effectiveFeedId = feedId ?? feeds[0]?.id ?? null
  const selectedFeed =
    feeds.find((feed) => feed.id === effectiveFeedId) || feeds[0] || null
  const messages = useMemo(
    () => resolveStaticMessages(source, pasted),
    [source, pasted]
  )
  const pastedCount = useMemo(() => parsePasted(pasted).length, [pasted])

  const groups = result?.groups ?? []
  const statusFor = (templateKey) => decisions[templateKey] || 'unreviewed'
  const acceptedGroups = useMemo(
    () => groups.filter((group) => statusFor(group.templateKey) === 'accepted'),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [groups, decisions]
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
      rejected: groups.filter((group) => statusFor(group.templateKey) === 'rejected')
        .length,
      review: groups.filter((group) => statusFor(group.templateKey) === 'unreviewed')
        .length,
      parsedSignals,
      coverage: candidates > 0 ? formatPercent(parsedSignals / candidates) : '0%'
    }
  }, [result, groups, audit, decisions]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // The feed source reuses the messages already stored for the connected feed
  // (GET /feeds/{id}/messages, the same deck the Label step reads); offline it
  // falls back to the bundled demo history so the prototype still runs.
  async function runFeedMining() {
    const useBackend = Boolean(authToken && onListMessages && effectiveFeedId)
    if (!useBackend) {
      finishMining(FEED_MESSAGES)
      return
    }
    setRunning(true)
    try {
      const response = await onListMessages(effectiveFeedId)
      finishMining(toChatMessages(response.messages || []))
    } catch (error) {
      fireToast?.(
        'rejected',
        'Could not load feed messages',
        error?.message || 'Try again in a moment.'
      )
    } finally {
      setRunning(false)
    }
  }

  function runMining() {
    if (source === 'feed') {
      void runFeedMining()
      return
    }
    finishMining(resolveStaticMessages(source, pasted))
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
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(templateKey)) next.delete(templateKey)
      else next.add(templateKey)
      return next
    })
  }

  const activeStage = !result
    ? 'messages'
    : acceptedGroups.length > 0
      ? 'audit'
      : 'review'

  return (
    <div className="vrs-page vrs-tm">
      <p className="vrs-tm__intro">
        Discover Telegram trading-signal formats by parsing messages into structured
        signal objects, grouping them into templates, and verifying format families
        instead of labelling thousands of individual messages. The parser is the
        classifier — everything here runs locally and deterministically, with no LLM.
      </p>

      <MiningPipelineRibbon activeId={activeStage} />

      <MiningSourcePanel
        source={source}
        onSourceChange={setSource}
        pasted={pasted}
        onPastedChange={setPasted}
        feeds={feeds}
        feedId={effectiveFeedId}
        onFeedChange={setFeedId}
        selectedFeedName={selectedFeed?.name}
        authenticated={Boolean(authToken)}
        demoFeedCount={FEED_MESSAGES.length}
        sampleCount={SAMPLE_MESSAGES.length}
        pastedCount={pastedCount}
        running={running}
        canRun={
          source === 'feed'
            ? Boolean(effectiveFeedId) || FEED_MESSAGES.length > 0
            : messages.length > 0
        }
        onRun={runMining}
      />

      {!result ? (
        <div className="vrs-empty vrs-empty--sm">
          <div className="vrs-empty__note">
            Pick a source and run the miner to discover signal-format families.
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
                    status={statusFor(group.templateKey)}
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
          />
        </>
      )}
    </div>
  )
}

export default TemplateMiningPage
