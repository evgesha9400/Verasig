# Pipeline Backend Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Label, Distill, and Verify pipeline steps render real backend data instead of `seed.js` placeholders, persisting labels per swipe; render a shared upsell placeholder for the deferred Exchange/Execution/Backtest steps.

**Architecture:** Mirror the existing `BackfillView` contract — `ProductApp` passes API-bound handler closures (over `authToken` + `chatId`) into each step view; the view fetches on mount and renders real data. A new `web/src/shared/api/pipelineApi.js` holds the request functions; a shared `web/src/shared/api/sse.js` holds one `EventSource` helper used by both backfill and distill.

**Tech Stack:** React 18, Vite 6, Vitest 3 + @testing-library/react (jsdom), the existing `requestJson` client. Backend is FastAPI (already implemented; no backend changes).

**Spec:** `docs/superpowers/specs/2026-06-15-pipeline-backend-wiring-design.md`
**Decision record:** `docs/adr/0011-defer-post-verify-routing-to-paid-tier.md`

---

## Conventions for every task

- All paths are relative to the repo root `/Users/evgesha/Projects/trading/Verasig`.
- Run a single test file from the web workspace:
  `cd apps/frontend/web && npx vitest run <path-from-web-root>`
- Run the whole frontend suite: `cd apps/frontend && make test`
- Lint: `cd apps/frontend && npm run lint --workspace verasig-web`
- Format before each commit: `cd apps/frontend && npm run format`
- Commit only the files listed in the task. **Do not** stage
  `apps/frontend/web/src/features/exchanges/ExchangesView.jsx` — it carries an
  unrelated pre-existing edit.

## File Structure

| File | Responsibility | Action |
| --- | --- | --- |
| `web/src/shared/api/sse.js` | One `EventSource` progress helper (`streamJobProgress`) | Create |
| `web/src/shared/api/pipelineApi.js` | Label/Distill/Verify request functions | Create (grown per phase) |
| `web/src/shared/api/chatsApi.js` | Backfill streaming reuses `sse.js` | Modify |
| `web/src/features/pipeline/steps/LabelView.jsx` | Fetch + persist labels | Rewrite |
| `web/src/features/pipeline/steps/DistillView.jsx` | Run distill job, render real rules | Rewrite |
| `web/src/features/pipeline/steps/VerifyView.jsx` | Fetch samples, submit verdicts | Rewrite |
| `web/src/features/pipeline/steps/PaidFeaturePlaceholder.jsx` | Upsell screen for deferred steps | Create |
| `web/src/app/ProductApp.jsx` | Pass handler closures; mount placeholder | Modify |
| `web/src/app/workflow/useWorkflowState.js` | Drop client-side label state | Modify |
| `web/src/features/pipeline/steps/LabelView.test.jsx` | Mocked-handler tests | Rewrite |
| `web/src/features/pipeline/steps/DistillView.test.jsx` | Mocked-handler tests | Create |
| `web/src/features/pipeline/steps/VerifyView.test.jsx` | Mocked-handler tests | Create |
| `web/src/shared/api/pipelineApi.test.js` | Request-shape tests | Create (grown per phase) |

---

# Phase 1 — Label

### Task 1.1: Label API functions

**Files:**
- Create: `apps/frontend/web/src/shared/api/pipelineApi.js`
- Test: `apps/frontend/web/src/shared/api/pipelineApi.test.js`

- [ ] **Step 1: Write the failing test**

Create `apps/frontend/web/src/shared/api/pipelineApi.test.js`:

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getLabelCounts,
  listMessages,
  recordLabel
} from './pipelineApi.js'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('pipelineApi — label', () => {
  it('lists messages with bearer auth', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ messages: [{ id: '1' }] }))

    const body = await listMessages('jwt-token', '7')

    expect(body.messages[0].id).toBe('1')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/messages', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('records a label as an idempotent upsert', async () => {
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await recordLabel('jwt-token', '7', '42', 'signal')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/chats/7/messages/42/label',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer jwt-token'
        },
        body: JSON.stringify({ label: 'signal' })
      }
    )
  })

  it('reads label counts', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ signalCount: 3, noiseCount: 2, modifierCount: 0, total: 5 })
    )

    const counts = await getLabelCounts('jwt-token', '7')

    expect(counts.signalCount).toBe(3)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/labels', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: FAIL — `Failed to resolve import "./pipelineApi.js"`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/frontend/web/src/shared/api/pipelineApi.js`:

```js
import { requestJson } from './client.js'

export function listMessages(token, chatId, limit) {
  const query = limit ? `?limit=${limit}` : ''
  return requestJson(`/chats/${chatId}/messages${query}`, { token })
}

export function recordLabel(token, chatId, msgId, label) {
  return requestJson(`/chats/${chatId}/messages/${msgId}/label`, {
    method: 'POST',
    token,
    body: { label }
  })
}

export function getLabelCounts(token, chatId) {
  return requestJson(`/chats/${chatId}/labels`, { token })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
git add apps/frontend/web/src/shared/api/pipelineApi.js apps/frontend/web/src/shared/api/pipelineApi.test.js
git commit -m "feat(pipeline): add label backend API client"
```

---

### Task 1.2: Rewrite LabelView to fetch + persist

**Files:**
- Rewrite: `apps/frontend/web/src/features/pipeline/steps/LabelView.jsx`
- Test: `apps/frontend/web/src/features/pipeline/steps/LabelView.test.jsx` (rewrite)

- [ ] **Step 1: Write the failing test**

Replace the entire contents of `apps/frontend/web/src/features/pipeline/steps/LabelView.test.jsx`:

```jsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LabelView } from './LabelView.jsx'

const messages = [
  { id: '101', author: 'Apex', date: 'Jun 6', time: '08:42', text: 'LONG BTC', media: null },
  { id: '102', author: 'Apex', date: 'Jun 6', time: '09:03', text: 'gm chat', media: null }
]

function renderView(overrides = {}) {
  const onListMessages = vi.fn().mockResolvedValue({ messages })
  const onGetCounts = vi
    .fn()
    .mockResolvedValue({ signalCount: 0, noiseCount: 0, modifierCount: 0, total: 0 })
  const onRecordLabel = vi.fn().mockResolvedValue(undefined)
  const onDistill = vi.fn()
  render(
    <LabelView
      chatId="7"
      onListMessages={onListMessages}
      onGetCounts={onGetCounts}
      onRecordLabel={onRecordLabel}
      onDistill={onDistill}
      {...overrides}
    />
  )
  return { onListMessages, onGetCounts, onRecordLabel, onDistill }
}

describe('LabelView', () => {
  it('loads real backfilled messages into the deck', async () => {
    const { onListMessages } = renderView()
    await waitFor(() => expect(onListMessages).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('LONG BTC')).toBeTruthy()
  })

  it('persists each label via the backend on swipe', async () => {
    const { onRecordLabel } = renderView()
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    await waitFor(() =>
      expect(onRecordLabel).toHaveBeenCalledWith('7', '101', 'signal')
    )
  })

  it('seeds the signal count from the backend and unlocks distill at five', async () => {
    const onGetCounts = vi
      .fn()
      .mockResolvedValue({ signalCount: 4, noiseCount: 0, modifierCount: 0, total: 4 })
    const onDistill = vi.fn()
    renderView({ onGetCounts, onDistill })
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    const distill = await screen.findByRole('button', { name: /Distill rules/i })
    expect(distill.disabled).toBe(false)
    fireEvent.click(distill)
    expect(onDistill).toHaveBeenCalled()
  })

  it('shows an empty state when there are no candidate messages', async () => {
    const onListMessages = vi.fn().mockResolvedValue({ messages: [] })
    renderView({ onListMessages })
    expect(await screen.findByText('No messages to label')).toBeTruthy()
  })

  it('reverts the optimistic label and reports an error when the write fails', async () => {
    const onRecordLabel = vi.fn().mockRejectedValue(new Error('boom'))
    const onError = vi.fn()
    renderView({ onRecordLabel, onError })
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    await waitFor(() => expect(onError).toHaveBeenCalled())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/LabelView.test.jsx`
Expected: FAIL — the current `LabelView` expects `messages`/`labels` props and never calls `onListMessages`.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `apps/frontend/web/src/features/pipeline/steps/LabelView.jsx`:

```jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { Button, IconButton } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Label step: Tinder-style signal / non-signal classification.
   Labeling is BINARY on purpose: a reply that is a signal is, by definition, an
   update (close / average / move stop) to the signal it quotes — Verasig derives
   that from the reply link, the user doesn't label it separately. The reply
   context is shown on the card; the parsed action gets confirmed at Verify.

   Data is backend-owned: the deck is the unlabeled candidate messages from
   GET /chats/{id}/messages; each swipe persists with POST .../label; the rail
   counts are seeded from GET /chats/{id}/labels and bumped locally. */
function MsgMedia({ kind }) {
  const map = {
    chart: ['chart', 'Chart screenshot'],
    image: ['image', 'Image'],
    doc: ['doc', 'Document']
  }
  const [icon, label] = map[kind] || ['image', 'Attachment']
  return (
    <div className="vrs-card-msg__media">
      <Icon name={icon} />
      <span>{label}</span>
    </div>
  )
}

function MessageCard({ msg, label, dragX = 0, isTop, style }) {
  const rot = dragX / 22
  const cls = `vrs-card-msg ${label === 'signal' ? 'is-signal' : ''} ${label === 'noise' ? 'is-noise' : ''}`
  const tStyle = isTop
    ? { transform: `translateX(${dragX}px) rotate(${rot}deg)`, ...style }
    : style
  return (
    <div className={cls} style={tStyle}>
      {isTop && (
        <>
          <span
            className="vrs-card-stamp signal"
            style={{ opacity: Math.max(0, Math.min(1, dragX / 90)) }}
          >
            Signal
          </span>
          <span
            className="vrs-card-stamp noise"
            style={{ opacity: Math.max(0, Math.min(1, -dragX / 90)) }}
          >
            Noise
          </span>
        </>
      )}
      <div className="vrs-card-msg__head">
        <span className="vrs-card-msg__av" style={{ background: 'var(--viz-2)' }}>
          {(msg.author || 'AC').slice(0, 2).toUpperCase()}
        </span>
        <span className="vrs-card-msg__who">{msg.author || 'Apex'}</span>
        {msg.replyTo && (
          <span className="vrs-autolink">
            <Icon name="reply" size={11} /> reply
          </span>
        )}
        <span className="vrs-card-msg__time">
          {msg.date} · {msg.time}
        </span>
      </div>
      <div className="vrs-card-msg__body">
        {msg.replyTo && (
          <div className="vrs-card-reply">
            <Icon name="reply" size={12} />
            <span className="vrs-card-reply__body">
              <span className="vrs-card-reply__who">{msg.replyTo.author}</span>
              <span className="vrs-card-reply__txt">{msg.replyTo.text}</span>
            </span>
          </div>
        )}
        <div className="vrs-card-msg__text">{msg.text}</div>
        {msg.media && <MsgMedia kind={msg.media} />}
      </div>
    </div>
  )
}

export function LabelView({
  chatId,
  onListMessages,
  onGetCounts,
  onRecordLabel,
  onDistill,
  onError
}) {
  const [messages, setMessages] = useState(null) // null while loading
  const [baseCounts, setBaseCounts] = useState({ signalCount: 0, noiseCount: 0 })
  const [labels, setLabels] = useState({}) // session map: msgId -> 'signal' | 'noise'
  const [idx, setIdx] = useState(0)
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // {dir, label}
  const dragRef = useRef({ active: false, startX: 0 })

  useEffect(() => {
    let active = true
    setMessages(null)
    Promise.all([onListMessages(chatId), onGetCounts(chatId)])
      .then(([messagesResult, counts]) => {
        if (!active) return
        setMessages(messagesResult.messages || [])
        setBaseCounts({
          signalCount: counts.signalCount || 0,
          noiseCount: counts.noiseCount || 0
        })
        setLabels({})
        setIdx(0)
      })
      .catch((error) => {
        if (!active) return
        setMessages([])
        onError &&
          onError('rejected', 'Could not load messages', error?.message || 'Try again.')
      })
    return () => {
      active = false
    }
  }, [chatId, onListMessages, onGetCounts, onError])

  const total = messages ? messages.length : 0
  const localSignal = Object.values(labels).filter((value) => value === 'signal').length
  const localNoise = Object.values(labels).filter((value) => value === 'noise').length
  const signalCount = baseCounts.signalCount + localSignal
  const noiseCount = baseCounts.noiseCount + localNoise
  const labeledCount = localSignal + localNoise
  const canDistill = signalCount >= 5
  const updateCount = (messages || []).filter(
    (m) => m.replyTo && labels[m.id] === 'signal'
  ).length

  const commit = useCallback(
    (label) => {
      if (!messages || idx >= total || flying) return
      const message = messages[idx]
      const dir = label === 'signal' ? 1 : -1
      const previous = labels[message.id]
      setFlying({ dir, label })
      setLabels((current) => ({ ...current, [message.id]: label }))
      Promise.resolve(onRecordLabel(chatId, message.id, label)).catch((error) => {
        setLabels((current) => {
          const next = { ...current }
          if (previous === undefined) delete next[message.id]
          else next[message.id] = previous
          return next
        })
        onError &&
          onError('rejected', 'Label not saved', error?.message || 'Try again.')
      })
      setTimeout(() => {
        setFlying(null)
        setDragX(0)
        setIdx((i) => Math.min(total, i + 1))
      }, 300)
    },
    [messages, idx, total, flying, labels, chatId, onRecordLabel, onError]
  )

  const goPrev = useCallback(() => {
    if (idx > 0 && !flying) {
      setIdx(idx - 1)
      setDragX(0)
    }
  }, [idx, flying])
  const goNext = useCallback(() => {
    if (idx < total && !flying) {
      setIdx(idx + 1)
      setDragX(0)
    }
  }, [idx, total, flying])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        commit('signal')
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        commit('noise')
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        goPrev()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        goNext()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [commit, goPrev, goNext])

  function onPointerDown(e) {
    if (idx >= total || flying) return
    dragRef.current = { active: true, startX: e.clientX }
    e.target.setPointerCapture && e.target.setPointerCapture(e.pointerId)
  }
  function onPointerMove(e) {
    if (!dragRef.current.active) return
    setDragX(e.clientX - dragRef.current.startX)
  }
  function onPointerUp() {
    if (!dragRef.current.active) return
    dragRef.current.active = false
    if (dragX > 110) commit('signal')
    else if (dragX < -110) commit('noise')
    else setDragX(0)
  }

  const loading = messages === null
  const empty = !loading && total === 0
  const atEnd = !loading && !empty && idx >= total
  const current = !loading && !empty && !atEnd ? messages[idx] : null
  const next1 = !loading && !empty && !atEnd ? messages[idx + 1] : null

  function renderStage() {
    if (loading) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-dot-pulse" />
          <div className="vrs-rail__note">Loading messages…</div>
        </div>
      )
    }
    if (empty) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="signals" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            No messages to label
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            This feed has no candidate signals to review yet.
          </div>
        </div>
      )
    }
    if (atEnd) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="check" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            Sample reviewed
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            {labeledCount} of {total} labelled. Press{' '}
            <kbd className="vrs-kbd">↑</kbd> to revisit, or distill rules from your
            signals.
          </div>
        </div>
      )
    }
    return (
      <>
        {next1 && (
          <MessageCard
            key={'bg' + next1.id}
            msg={next1}
            label={labels[next1.id]}
            isTop={false}
            style={{ transform: 'scale(0.95) translateY(14px)', opacity: 0.6 }}
          />
        )}
        <MessageCard
          key={current.id}
          msg={current}
          label={labels[current.id]}
          isTop={true}
          dragX={flying ? flying.dir * 600 : dragX}
          style={
            flying
              ? {
                  transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
                  transform: `translateX(${flying.dir * 600}px) rotate(${flying.dir * 18}deg)`
                }
              : dragRef.current.active
                ? {}
                : { transition: 'transform 0.25s var(--ease-out)' }
          }
        />
      </>
    )
  }

  return (
    <div className="vrs-label">
      <div className="vrs-deck">
        <div
          className="vrs-deck__stage"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{
            cursor: current ? (dragRef.current.active ? 'grabbing' : 'grab') : 'default'
          }}
        >
          {renderStage()}
        </div>

        <div className="vrs-swipe-controls">
          <IconButton
            variant="solid"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--no"
            label="Non-signal"
            onClick={() => commit('noise')}
            disabled={atEnd || loading || empty}
            title="Non-signal (←)"
          >
            <Icon name="x" size={22} />
          </IconButton>
          <div className="vrs-deck__nav">
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Previous"
              onClick={goPrev}
              disabled={idx === 0}
              title="Previous (↑)"
            >
              <Icon name="arrowUp" size={18} />
            </IconButton>
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Next"
              onClick={goNext}
              disabled={atEnd || loading || empty}
              title="Next (↓)"
            >
              <Icon name="arrowDown" size={18} />
            </IconButton>
          </div>
          <IconButton
            variant="accent"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--yes"
            label="Signal"
            onClick={() => commit('signal')}
            disabled={atEnd || loading || empty}
            title="Signal (→)"
          >
            <Icon name="check" size={22} />
          </IconButton>
        </div>
        <div className="vrs-deck__hint">
          <kbd>←</kbd> Non-signal &nbsp;·&nbsp; <kbd>→</kbd> Signal &nbsp;·&nbsp;{' '}
          <kbd>↑</kbd> Back &nbsp;·&nbsp; <kbd>↓</kbd> Skip
        </div>
      </div>

      <div className="vrs-rail">
        <div className="vrs-rail__h">Label messages</div>
        <div className="vrs-rail__note">
          Swipe right for trade signals, left for chatter, promos and noise. A signal
          that replies to an earlier signal is treated as an update to it — closes,
          averages and stop moves included.
        </div>

        <div className="vrs-rail__counts">
          <div className="vrs-count-card signal">
            <div className="vrs-count-card__v">{signalCount}</div>
            <div className="vrs-count-card__l">Signal</div>
          </div>
          <div className="vrs-count-card noise">
            <div className="vrs-count-card__v">{noiseCount}</div>
            <div className="vrs-count-card__l">Non-signal</div>
          </div>
        </div>

        {updateCount > 0 && (
          <div className="vrs-rail__derived">
            <Icon name="reply" size={13} />
            <span>
              <strong>{updateCount}</strong> of your signals{' '}
              {updateCount === 1 ? 'is a reply' : 'are replies'} — they&rsquo;ll be
              linked to the signal they quote as updates, not opened as new positions.
            </span>
          </div>
        )}

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Reviewed</span>
            <span>
              {labeledCount} / {total}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${total ? (labeledCount / total) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Signals to distill</span>
            <span>{Math.min(signalCount, 5)} / 5</span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${Math.min(signalCount / 5, 1) * 100}%` }} />
          </div>
        </div>

        <div className="vrs-rail__done">
          <Button
            variant="primary"
            fullWidth
            disabled={!canDistill}
            onClick={onDistill}
            iconLeft={<Icon name="sparkles" size={16} />}
          >
            {canDistill
              ? 'Distill rules'
              : `Label ${5 - signalCount} more signal${5 - signalCount === 1 ? '' : 's'}`}
          </Button>
          {!canDistill && (
            <div
              className="vrs-rail__note"
              style={{ marginTop: 10, textAlign: 'center' }}
            >
              Distillation unlocks at 5 labelled signals.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const STAGE_CENTER = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  textAlign: 'center',
  padding: 30
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/LabelView.test.jsx`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/features/pipeline/steps/LabelView.jsx apps/frontend/web/src/features/pipeline/steps/LabelView.test.jsx
git commit -m "feat(label): render and persist real backfilled messages"
```

---

### Task 1.3: Wire ProductApp + prune label state from useWorkflowState

**Files:**
- Modify: `apps/frontend/web/src/app/ProductApp.jsx`
- Modify: `apps/frontend/web/src/app/workflow/useWorkflowState.js`

- [ ] **Step 1: Prune label state from `useWorkflowState.js`**

In `apps/frontend/web/src/app/workflow/useWorkflowState.js`:

1. Delete the `labelsByChat` state line:
```js
  const [labelsByChat, setLabelsByChat] = useState(saved ? saved.labelsByChat : {})
```

2. In the `localStorage.setItem` payload object, delete the `labelsByChat,` line, and delete `labelsByChat` from that effect's dependency array.

3. Delete the derived label values block:
```js
  const labels = (activeChatId && labelsByChat[activeChatId]) || {}
  const signalCount = Object.values(labels).filter(
    (value) => value === 'signal' || value === 'modifier'
  ).length
  const noiseCount = Object.values(labels).filter((value) => value === 'noise').length
```

4. Delete the `setLabel` function:
```js
  function setLabel(msgId, label) {
    setLabelsByChat((current) => ({
      ...current,
      [activeChatId]: {
        ...(current[activeChatId] || {}),
        [msgId]: label
      }
    }))
  }
```

5. In `restartChat`, delete the label-clearing block:
```js
    setLabelsByChat((current) => {
      const next = { ...current }
      delete next[chat.id]
      return next
    })
```

6. In the returned object, delete the lines `labelsByChat,`, `labels,`, `signalCount,`, `noiseCount,`, and `setLabel,`.

- [ ] **Step 2: Wire `LabelView` in `ProductApp.jsx`**

In `apps/frontend/web/src/app/ProductApp.jsx`:

1. Add the import after the `chatsApi` import block:
```js
import {
  getLabelCounts,
  listMessages,
  recordLabel
} from '../shared/api/pipelineApi.js'
```

2. Remove `MESSAGES` from the seed import. Change:
```js
import { MESSAGES } from '../domain/demo-data/seed.js'
```
to delete that line entirely (no other symbol from it is used here).

3. In the destructure of `useWorkflowState(authToken)`, remove `labels,`, `signalCount,`, `noiseCount,`, and `setLabel,`.

4. Replace the `screen === 'label'` body:
```jsx
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
```
with:
```jsx
    } else if (screen === 'label') {
      body = (
        <LabelView
          chatId={activeChat.id}
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
```

- [ ] **Step 3: Run the full frontend suite + lint**

Run:
```bash
cd apps/frontend && npm run lint --workspace verasig-web && make test
```
Expected: PASS. If `AppRouter.test.jsx` references removed `useWorkflowState` fields, it does not (it drives routing only) — but if any test fails because it imported `setLabel`/`labels`, update that test to drop the reference. Do not weaken assertions.

- [ ] **Step 4: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/app/ProductApp.jsx apps/frontend/web/src/app/workflow/useWorkflowState.js
git commit -m "feat(label): wire LabelView to backend, drop client-side label state"
```

---

### Task 1.4: Verify Label end-to-end against the real feed

**Files:** none (manual verification).

- [ ] **Step 1: Start the stack**

Run (in a background terminal): `make up` (or `make dev`). Wait for `http://localhost:8000/health` to return ok and the frontend on `http://localhost:5173`.

- [ ] **Step 2: Walk the step**

Log in, open the real backfilled feed, enter the Label step. Confirm:
- Real backfilled message text appears on the cards (not the seed "LONG BTC/USDT … 64,200" sample).
- Each swipe issues `POST /chats/{id}/messages/{id}/label` returning `204` (check the Network tab).
- The "Signal" rail count increments and "Distill rules" unlocks at 5 signals.
- Reloading the page and re-entering Label shows fewer cards (labelled ones drop out) and the seeded count reflects prior labels.
- No errors in the browser console or network tab.

- [ ] **Step 3: Record the result**

If anything fails, STOP and debug before Phase 2. If it passes, note it in the task tracker and continue.

---

# Phase 2 — Distill

### Task 2.1: Extract a shared SSE helper and reuse it for backfill

**Files:**
- Create: `apps/frontend/web/src/shared/api/sse.js`
- Modify: `apps/frontend/web/src/shared/api/chatsApi.js`
- Modify: `apps/frontend/web/src/shared/api/chatsApi.test.js` (no behaviour change — keep as-is; it must still pass)

- [ ] **Step 1: Write the failing test**

Append a new file `apps/frontend/web/src/shared/api/sse.test.js`:

```js
import { describe, expect, it, vi } from 'vitest'
import { streamJobProgress } from './sse.js'

class FakeEventSource {
  constructor(url) {
    this.url = url
    this.closed = false
    this.listeners = {}
    FakeEventSource.last = this
  }
  addEventListener(type, listener) {
    this.listeners[type] = listener
  }
  close() {
    this.closed = true
  }
  emit(type, data) {
    this.listeners[type]({ data: data === undefined ? undefined : JSON.stringify(data) })
  }
}

describe('streamJobProgress', () => {
  it('builds the URL with the token query param and wires events', () => {
    globalThis.EventSource = FakeEventSource
    const onProgress = vi.fn()
    const onDone = vi.fn()

    streamJobProgress('jwt-token', '/chats/7/distill/progress', { onProgress, onDone })
    const source = FakeEventSource.last

    expect(source.url).toBe(
      'http://localhost:8000/chats/7/distill/progress?token=jwt-token'
    )
    source.emit('progress', { phase: 'Reading your labelled signals' })
    source.emit('done', { rules: 5 })

    expect(onProgress).toHaveBeenCalledWith({ phase: 'Reading your labelled signals' })
    expect(onDone).toHaveBeenCalledWith({ rules: 5 })
    expect(source.closed).toBe(true)
  })

  it('closes and reports on an error event', () => {
    globalThis.EventSource = FakeEventSource
    const onError = vi.fn()

    streamJobProgress('jwt-token', '/chats/7/distill/progress', { onError })
    const source = FakeEventSource.last
    source.emit('error', undefined)

    expect(onError).toHaveBeenCalledWith({})
    expect(source.closed).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/sse.test.js`
Expected: FAIL — `Failed to resolve import "./sse.js"`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/frontend/web/src/shared/api/sse.js`:

```js
import { createApiUrl } from './client.js'

function parseEventData(event) {
  if (!event.data) return {}
  return JSON.parse(event.data)
}

function progressUrl(token, path) {
  const url = new URL(createApiUrl(path))
  url.searchParams.set('token', token)
  return url.toString()
}

export function streamJobProgress(token, path, handlers = {}) {
  const source = new EventSource(progressUrl(token, path))

  source.addEventListener('progress', (event) => {
    handlers.onProgress && handlers.onProgress(parseEventData(event))
  })
  source.addEventListener('done', (event) => {
    handlers.onDone && handlers.onDone(parseEventData(event))
    source.close()
  })
  source.addEventListener('error', (event) => {
    handlers.onError && handlers.onError(parseEventData(event))
    source.close()
  })

  return {
    close: () => source.close()
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/sse.test.js`
Expected: PASS (2 tests).

- [ ] **Step 5: Refactor `chatsApi.js` to reuse it**

In `apps/frontend/web/src/shared/api/chatsApi.js`, replace the local `parseEventData`, `createProgressUrl`, and `streamBackfillProgress` definitions with a delegation. The final file is:

```js
import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

export function listChats(token) {
  return requestJson('/chats', { token })
}

export function createChat(token, tag) {
  return requestJson('/chats', {
    method: 'POST',
    token,
    body: { tag }
  })
}

export function deleteChat(token, chatId) {
  return requestJson(`/chats/${chatId}`, {
    method: 'DELETE',
    token
  })
}

export function startBackfill(token, chatId) {
  return requestJson(`/chats/${chatId}/backfill`, {
    method: 'POST',
    token
  })
}

export function cancelBackfill(token, chatId) {
  return requestJson(`/chats/${chatId}/backfill/cancel`, {
    method: 'POST',
    token
  })
}

export function streamBackfillProgress(token, chatId, handlers = {}) {
  return streamJobProgress(token, `/chats/${chatId}/backfill/progress`, handlers)
}
```

- [ ] **Step 6: Run the backfill streaming test to verify no regression**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/chatsApi.test.js`
Expected: PASS (existing tests unchanged).

- [ ] **Step 7: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/shared/api/sse.js apps/frontend/web/src/shared/api/sse.test.js apps/frontend/web/src/shared/api/chatsApi.js
git commit -m "refactor(api): extract shared streamJobProgress SSE helper"
```

---

### Task 2.2: Distill API functions

**Files:**
- Modify: `apps/frontend/web/src/shared/api/pipelineApi.js`
- Modify: `apps/frontend/web/src/shared/api/pipelineApi.test.js`

- [ ] **Step 1: Write the failing test**

Append these tests inside `apps/frontend/web/src/shared/api/pipelineApi.test.js` (add `getRules`, `startDistill` to the import, and `streamDistillProgress`):

```js
describe('pipelineApi — distill', () => {
  it('starts a distill job', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ jobId: 'u:7:distill' }, 202))

    const body = await startDistill('jwt-token', '7')

    expect(body.jobId).toBe('u:7:distill')
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/distill', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('reads compiled rules', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ rules: [{ id: 'r:0', label: 'has verb', detail: '…', match: 94 }] })
    )

    const body = await getRules('jwt-token', '7')

    expect(body.rules[0].match).toBe(94)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/rules', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('streams distill progress via the shared helper', () => {
    class FakeEventSource {
      constructor(url) {
        this.url = url
        this.listeners = {}
        FakeEventSource.last = this
      }
      addEventListener(type, listener) {
        this.listeners[type] = listener
      }
      close() {
        this.closed = true
      }
    }
    globalThis.EventSource = FakeEventSource

    streamDistillProgress('jwt-token', '7', {})

    expect(FakeEventSource.last.url).toBe(
      'http://localhost:8000/chats/7/distill/progress?token=jwt-token'
    )
  })
})
```

Update the import at the top of the file to:
```js
import {
  getLabelCounts,
  getRules,
  listMessages,
  recordLabel,
  startDistill,
  streamDistillProgress
} from './pipelineApi.js'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: FAIL — `startDistill`/`getRules`/`streamDistillProgress` are not exported.

- [ ] **Step 3: Write minimal implementation**

Append to `apps/frontend/web/src/shared/api/pipelineApi.js` (and add the `sse.js` import at the top):

```js
import { streamJobProgress } from './sse.js'

export function startDistill(token, chatId) {
  return requestJson(`/chats/${chatId}/distill`, { method: 'POST', token })
}

export function streamDistillProgress(token, chatId, handlers = {}) {
  return streamJobProgress(token, `/chats/${chatId}/distill/progress`, handlers)
}

export function getRules(token, chatId) {
  return requestJson(`/chats/${chatId}/rules`, { token })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: PASS (all label + distill tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/shared/api/pipelineApi.js apps/frontend/web/src/shared/api/pipelineApi.test.js
git commit -m "feat(distill): add distill backend API client"
```

---

### Task 2.3: Rewrite DistillView to run the real job

**Files:**
- Rewrite: `apps/frontend/web/src/features/pipeline/steps/DistillView.jsx`
- Create: `apps/frontend/web/src/features/pipeline/steps/DistillView.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `apps/frontend/web/src/features/pipeline/steps/DistillView.test.jsx`:

```jsx
import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DistillView } from './DistillView.jsx'

function renderView(overrides = {}) {
  const onStartDistill = vi.fn().mockResolvedValue({ jobId: 'u:7:distill' })
  let streamHandlers
  const onStreamProgress = vi.fn((_chatId, handlers) => {
    streamHandlers = handlers
    return { close: vi.fn() }
  })
  const onGetRules = vi.fn().mockResolvedValue({
    rules: [{ id: 'r:0', label: 'Has a directional verb', detail: 'LONG/SHORT', match: 94 }]
  })
  const onComplete = vi.fn()
  render(
    <DistillView
      chatId="7"
      onStartDistill={onStartDistill}
      onStreamProgress={onStreamProgress}
      onGetRules={onGetRules}
      onComplete={onComplete}
      {...overrides}
    />
  )
  return { onStartDistill, onStreamProgress, onGetRules, onComplete, getHandlers: () => streamHandlers }
}

describe('DistillView', () => {
  it('starts the distill job and streams phases', async () => {
    const { onStartDistill, getHandlers } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    expect(onStartDistill).toHaveBeenCalledWith('7')
    act(() => getHandlers().onProgress({ phase: 'Extracting structure & tickers' }))
    expect(screen.getByText('Extracting structure & tickers')).toBeTruthy()
  })

  it('fetches and renders real rules on done, with match as a percentage', async () => {
    const { getHandlers, onGetRules } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onDone({ rules: 1 })
      await Promise.resolve()
    })
    await waitFor(() => expect(onGetRules).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('Has a directional verb')).toBeTruthy()
    expect(screen.getByText('94%')).toBeTruthy()
  })

  it('recovers rules when the stream errors (job already evicted)', async () => {
    const { getHandlers, onGetRules } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onError({})
      await Promise.resolve()
    })
    await waitFor(() => expect(onGetRules).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('Has a directional verb')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/DistillView.test.jsx`
Expected: FAIL — current `DistillView` takes only `onComplete` and uses seed data + timers.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `apps/frontend/web/src/features/pipeline/steps/DistillView.jsx`:

```jsx
import { useState, useEffect } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Distill step: backend distills filtering rules from the labels.
   POST /distill starts the job; SSE streams the five phases; GET /rules returns
   the compiled ruleset (match is already a 0–100 percentage). */
function ThinkOrb() {
  return (
    <svg className="vrs-think__orb" viewBox="0 0 86 86" fill="none">
      <circle cx="43" cy="43" r="30" stroke="var(--border-strong)" strokeWidth="1.5" />
      <circle
        cx="43"
        cy="43"
        r="30"
        stroke="var(--signal-500)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeDasharray="48 140"
        style={{ filter: 'drop-shadow(0 0 5px var(--signal-glow))' }}
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 43 43"
          to="360 43 43"
          dur="1.1s"
          repeatCount="indefinite"
        />
      </circle>
      <path
        d="M28 43 L37 43 L41 33 L46 53 L50 43 L58 43"
        stroke="var(--signal-500)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/* Must match the backend DISTILL_PHASES strings exactly (distill_routes.py). */
const DISTILL_STEPS = [
  'Reading your labelled signals',
  'Extracting structure & tickers',
  'Inferring discriminative patterns',
  'Cross-checking against non-signals',
  'Compiling filter ruleset'
]

export function DistillView({
  chatId,
  onStartDistill,
  onStreamProgress,
  onGetRules,
  onComplete,
  onError
}) {
  const [phase, setPhase] = useState('thinking') // 'thinking' | 'done' | 'error'
  const [step, setStep] = useState(0)
  const [rules, setRules] = useState([])

  // No start-once ref: mirror BackfillView. In React StrictMode the effect runs
  // twice; the first run's cleanup sets closed=true (so it never subscribes) and
  // the second run re-POSTs. A duplicate POST returns 409, which we tolerate and
  // stream the already-running job. In production the effect runs once.
  useEffect(() => {
    let closed = false
    let subscription = null

    function loadRules() {
      return Promise.resolve(onGetRules(chatId)).then((result) => {
        if (closed) return
        setRules(result.rules || [])
        setPhase('done')
      })
    }

    function fail() {
      if (closed) return
      setPhase('error')
      onError &&
        onError('rejected', 'Distillation failed', 'The distill job did not complete.')
    }

    async function run() {
      try {
        await onStartDistill(chatId)
      } catch (error) {
        // A duplicated start (StrictMode / resume) is fine — stream the running job.
        if (error?.status !== 409) {
          if (!closed) {
            setPhase('error')
            onError &&
              onError('rejected', 'Distillation failed', error?.message || 'Try again.')
          }
          return
        }
      }
      if (closed) return
      subscription = onStreamProgress(chatId, {
        onProgress: (progress) => {
          if (!progress.phase) return
          const index = DISTILL_STEPS.indexOf(progress.phase)
          if (index >= 0) setStep(index + 1)
        },
        // On done OR on a stream error, read the durable ruleset. The job may have
        // finished and been evicted before we connected (distill has no replay),
        // so reading /rules is the source of truth; only fail if that read fails.
        onDone: () => {
          loadRules().catch(fail)
        },
        onError: () => {
          loadRules().catch(fail)
        }
      })
    }

    void run()

    return () => {
      closed = true
      subscription && subscription.close()
    }
  }, [chatId, onStartDistill, onStreamProgress, onGetRules, onError])

  if (phase === 'thinking') {
    return (
      <div className="vrs-think vrs-fade-in">
        <ThinkOrb />
        <div>
          <div className="vrs-think__title">Distilling signal rules</div>
          <div className="vrs-think__sub">
            Verasig is analysing your labels to learn what makes a message a tradeable
            signal.
          </div>
        </div>
        <div className="vrs-think__steps">
          {DISTILL_STEPS.map((s, i) => (
            <div
              key={i}
              className={`vrs-think__step ${i < step ? 'is-done' : ''} ${i === step ? 'is-active' : ''}`}
            >
              <span className="vrs-think__tick">
                {i < step ? (
                  <Icon name="check" size={14} style={{ color: 'var(--accent-text)' }} />
                ) : i === step ? (
                  <span className="vrs-dot-pulse" />
                ) : (
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      border: '1px solid var(--border-strong)'
                    }}
                  />
                )}
              </span>
              {s}
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="vrs-think vrs-fade-in" style={{ maxWidth: 520 }}>
        <span
          className="vrs-rule__ic"
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            background: 'var(--rejected-bg)',
            color: 'var(--rejected-500)'
          }}
        >
          <Icon name="alert" size={26} />
        </span>
        <div>
          <div className="vrs-think__title">Distillation didn’t complete</div>
          <div className="vrs-think__sub">
            Something interrupted the distill job. Go back and try again.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="vrs-page vrs-fade-in" style={{ maxWidth: 720 }}>
      <div className="vrs-setup__hero" style={{ alignItems: 'flex-start' }}>
        <span className="vrs-rule__ic" style={{ width: 44, height: 44, borderRadius: 10 }}>
          <Icon name="sparkles" size={22} />
        </span>
        <div>
          <div className="vrs-setup__title" style={{ fontSize: 'var(--text-xl)' }}>
            {rules.length} rule{rules.length === 1 ? '' : 's'} distilled
          </div>
          <div className="vrs-setup__sub">
            These rules now classify the rest of the feed history. Verify a random
            sample below before we extract.
          </div>
        </div>
      </div>

      <div className="vrs-rules">
        {rules.map((r, i) => (
          <div
            key={r.id}
            className="vrs-rule vrs-fade-in"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <span className="vrs-rule__ic">
              <Icon name="check" size={15} />
            </span>
            <div>
              <div className="vrs-rule__lbl">{r.label}</div>
              <div className="vrs-rule__detail">{r.detail}</div>
            </div>
            <span className="vrs-rule__match">{Math.round(r.match)}%</span>
          </div>
        ))}
      </div>

      <div className="vrs-form__actions">
        <Button
          variant="primary"
          size="lg"
          iconRight={<Icon name="arrowRight" size={16} />}
          onClick={onComplete}
        >
          Verify on new messages
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/DistillView.test.jsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/features/pipeline/steps/DistillView.jsx apps/frontend/web/src/features/pipeline/steps/DistillView.test.jsx
git commit -m "feat(distill): run real distill job and render compiled rules"
```

---

### Task 2.4: Wire DistillView in ProductApp + verify

**Files:**
- Modify: `apps/frontend/web/src/app/ProductApp.jsx`

- [ ] **Step 1: Update the imports**

In `apps/frontend/web/src/app/ProductApp.jsx`, extend the `pipelineApi` import to:
```js
import {
  getLabelCounts,
  getRules,
  listMessages,
  recordLabel,
  startDistill,
  streamDistillProgress
} from '../shared/api/pipelineApi.js'
```

- [ ] **Step 2: Replace the distill body**

Replace:
```jsx
    } else if (screen === 'distill') {
      body = <DistillView onComplete={() => setScreen('verify')} />
    } else if (screen === 'verify') {
```
with:
```jsx
    } else if (screen === 'distill') {
      body = (
        <DistillView
          chatId={activeChat.id}
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
```

- [ ] **Step 3: Lint + full suite**

Run: `cd apps/frontend && npm run lint --workspace verasig-web && make test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/app/ProductApp.jsx
git commit -m "feat(distill): wire DistillView to backend distill job"
```

- [ ] **Step 5: Verify end-to-end**

With the stack running, label ≥5 signals on the real feed, click **Distill rules**. Confirm: `POST /distill` returns `202`; the SSE phases advance through the five steps; on completion real rules render with percentage matches; **Verify on new messages** advances to Verify. No console/network errors.

---

# Phase 3 — Verify

### Task 3.1: Verify API functions

**Files:**
- Modify: `apps/frontend/web/src/shared/api/pipelineApi.js`
- Modify: `apps/frontend/web/src/shared/api/pipelineApi.test.js`

- [ ] **Step 1: Write the failing test**

Add `getVerifySamples`, `submitVerify` to the import in `pipelineApi.test.js` and append:

```js
describe('pipelineApi — verify', () => {
  it('gets verification samples', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse({ attempt: 1, samples: [{ id: '1', predicted: 'signal' }] })
    )

    const body = await getVerifySamples('jwt-token', '7')

    expect(body.attempt).toBe(1)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/verify/samples', {
      method: 'GET',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('submits verdicts', async () => {
    fetch.mockResolvedValueOnce(jsonResponse({ passed: true, misclassified: [] }))
    const verdicts = [{ messageId: '1', verdict: 'correct' }]

    const body = await submitVerify('jwt-token', '7', verdicts)

    expect(body.passed).toBe(true)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/chats/7/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({ verdicts })
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: FAIL — `getVerifySamples`/`submitVerify` not exported.

- [ ] **Step 3: Write minimal implementation**

Append to `apps/frontend/web/src/shared/api/pipelineApi.js`:

```js
export function getVerifySamples(token, chatId) {
  return requestJson(`/chats/${chatId}/verify/samples`, { token })
}

export function submitVerify(token, chatId, verdicts) {
  return requestJson(`/chats/${chatId}/verify`, {
    method: 'POST',
    token,
    body: { verdicts }
  })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: PASS (all label + distill + verify tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/shared/api/pipelineApi.js apps/frontend/web/src/shared/api/pipelineApi.test.js
git commit -m "feat(verify): add verify backend API client"
```

---

### Task 3.2: Rewrite VerifyView to fetch samples + submit verdicts

**Files:**
- Rewrite: `apps/frontend/web/src/features/pipeline/steps/VerifyView.jsx`
- Create: `apps/frontend/web/src/features/pipeline/steps/VerifyView.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `apps/frontend/web/src/features/pipeline/steps/VerifyView.test.jsx`:

```jsx
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { VerifyView } from './VerifyView.jsx'

const samples = Array.from({ length: 6 }, (_, i) => ({
  id: String(i + 1),
  author: 'Apex',
  date: 'Jun 6',
  time: '08:42',
  text: `msg ${i + 1}`,
  media: null,
  predicted: i % 2 === 0 ? 'signal' : 'noise'
}))

function renderView(overrides = {}) {
  const onGetSamples = vi.fn().mockResolvedValue({ attempt: 1, samples })
  const onSubmit = vi.fn().mockResolvedValue({ passed: true, misclassified: [] })
  const onPass = vi.fn()
  const onStop = vi.fn()
  const onLoop = vi.fn()
  render(
    <VerifyView
      chatId="7"
      onGetSamples={onGetSamples}
      onSubmit={onSubmit}
      onPass={onPass}
      onStop={onStop}
      onLoop={onLoop}
      {...overrides}
    />
  )
  return { onGetSamples, onSubmit, onPass, onStop, onLoop }
}

describe('VerifyView', () => {
  it('loads samples from the backend', async () => {
    const { onGetSamples } = renderView()
    await waitFor(() => expect(onGetSamples).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('msg 1')).toBeTruthy()
  })

  it('submits verdicts and shows the pass screen when the backend passes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const { onSubmit } = renderView()
      await screen.findByText('msg 1')
      // Each swipe sets a 300ms "flying" guard that blocks the next commit, so
      // advance past it between clicks (the real user waits for the animation).
      for (let i = 0; i < 6; i += 1) {
        fireEvent.click(screen.getByRole('button', { name: 'Correct' }))
        act(() => vi.advanceTimersByTime(320))
      }
      fireEvent.click(screen.getByRole('button', { name: /Finish verification/i }))
      await waitFor(() => expect(onSubmit).toHaveBeenCalled())
      expect(onSubmit.mock.calls[0][0]).toBe('7')
      expect(onSubmit.mock.calls[0][1]).toHaveLength(6)
      expect(await screen.findByText('Verification passed')).toBeTruthy()
    } finally {
      vi.useRealTimers()
    }
  })

  it('loops back to labelling when the backend fails verification', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const onSubmit = vi.fn().mockResolvedValue({ passed: false, misclassified: ['2'] })
      const { onLoop } = renderView({ onSubmit })
      await screen.findByText('msg 1')
      for (let i = 0; i < 6; i += 1) {
        fireEvent.click(screen.getByRole('button', { name: 'Correct' }))
        act(() => vi.advanceTimersByTime(320))
      }
      fireEvent.click(screen.getByRole('button', { name: /Finish verification/i }))
      fireEvent.click(await screen.findByRole('button', { name: /Back to labelling/i }))
      expect(onLoop).toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/VerifyView.test.jsx`
Expected: FAIL — current `VerifyView` reads seed `MESSAGES` and takes `attempt` only.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `apps/frontend/web/src/features/pipeline/steps/VerifyView.jsx`:

```jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { Badge, Button, IconButton, InteractiveCard } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — Verify step: confirm the ruleset's classifications on a fresh sample.
   Samples and their predictions come from GET /chats/{id}/verify/samples; the
   verdicts POST to /chats/{id}/verify, and the BACKEND decides pass/fail. */
const VERIFY_MIN = 6

function VerifyMedia({ kind }) {
  const map = {
    chart: ['chart', 'Chart screenshot'],
    image: ['image', 'Image'],
    doc: ['doc', 'Document']
  }
  const [icon, label] = map[kind] || ['image', 'Attachment']
  return (
    <div className="vrs-card-msg__media">
      <Icon name={icon} />
      <span>{label}</span>
    </div>
  )
}

function VerifyCard({ item, dragX = 0, isTop, style }) {
  const rot = dragX / 22
  const tStyle = isTop
    ? { transform: `translateX(${dragX}px) rotate(${rot}deg)`, ...style }
    : style
  const isSignal = item.predicted === 'signal'
  const cls = `vrs-card-msg ${isSignal ? 'is-signal' : 'is-noise'}`
  return (
    <div className={cls} style={tStyle}>
      {isTop && (
        <>
          <span
            className="vrs-card-stamp signal"
            style={{ opacity: Math.max(0, Math.min(1, dragX / 90)) }}
          >
            Correct
          </span>
          <span
            className="vrs-card-stamp noise"
            style={{ opacity: Math.max(0, Math.min(1, -dragX / 90)) }}
          >
            Wrong
          </span>
        </>
      )}
      <div className="vrs-card-msg__head">
        <Badge tone={isSignal ? 'verified' : 'rejected'} dot>
          {isSignal ? 'Classified: Signal' : 'Classified: Non-signal'}
        </Badge>
        <span className="vrs-card-msg__time" style={{ marginLeft: 'auto' }}>
          auto · rule match
        </span>
      </div>
      <div className="vrs-card-msg__body">
        {item.replyTo && (
          <div className="vrs-card-reply">
            <Icon name="reply" size={12} />
            <span className="vrs-card-reply__body">
              <span className="vrs-card-reply__who">{item.replyTo.author}</span>
              <span className="vrs-card-reply__txt">{item.replyTo.text}</span>
            </span>
          </div>
        )}
        <div className="vrs-card-msg__text">{item.text}</div>
        {item.media && <VerifyMedia kind={item.media} />}
      </div>
    </div>
  )
}

export function VerifyView({ chatId, onGetSamples, onSubmit, onPass, onStop, onLoop, onError }) {
  const [items, setItems] = useState(null) // null while loading
  const [idx, setIdx] = useState(0)
  const [marks, setMarks] = useState({}) // id -> 'correct' | 'wrong'
  const [dragX, setDragX] = useState(0)
  const [flying, setFlying] = useState(null) // { dir, verdict }
  const [result, setResult] = useState(null) // null | 'pass' | 'loop'
  const [submitting, setSubmitting] = useState(false)
  const dragRef = useRef({ active: false, startX: 0 })

  useEffect(() => {
    let active = true
    setItems(null)
    Promise.resolve(onGetSamples(chatId))
      .then((body) => {
        if (!active) return
        setItems(body.samples || [])
        setIdx(0)
      })
      .catch((error) => {
        if (!active) return
        setItems([])
        onError &&
          onError('rejected', 'Could not load samples', error?.message || 'Try again.')
      })
    return () => {
      active = false
    }
  }, [chatId, onGetSamples, onError])

  const total = items ? items.length : 0
  const verifiedCount = Object.keys(marks).length
  const correctCount = Object.values(marks).filter((v) => v === 'correct').length
  const flaggedCount = Object.values(marks).filter((v) => v === 'wrong').length
  const minMet = verifiedCount >= VERIFY_MIN

  const commit = useCallback(
    (verdict) => {
      if (!items || idx >= total || flying) return
      const dir = verdict === 'correct' ? 1 : -1
      const id = items[idx].id
      setFlying({ dir, verdict })
      setMarks((m) => ({ ...m, [id]: verdict }))
      setTimeout(() => {
        setFlying(null)
        setDragX(0)
        setIdx((i) => Math.min(total, i + 1))
      }, 300)
    },
    [items, idx, total, flying]
  )

  const goPrev = useCallback(() => {
    if (idx > 0 && !flying) {
      setIdx(idx - 1)
      setDragX(0)
    }
  }, [idx, flying])
  const goNext = useCallback(() => {
    if (idx < total && !flying) {
      setIdx(idx + 1)
      setDragX(0)
    }
  }, [idx, total, flying])

  function finish() {
    if (!minMet || submitting) return
    const verdicts = Object.entries(marks).map(([messageId, verdict]) => ({
      messageId,
      verdict
    }))
    setSubmitting(true)
    Promise.resolve(onSubmit(chatId, verdicts))
      .then((body) => {
        setResult(body.passed ? 'pass' : 'loop')
      })
      .catch((error) => {
        onError &&
          onError('rejected', 'Could not submit verdicts', error?.message || 'Try again.')
      })
      .finally(() => setSubmitting(false))
  }

  useEffect(() => {
    if (result) return
    function onKey(e) {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        commit('correct')
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        commit('wrong')
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        goPrev()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        goNext()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [commit, goPrev, goNext, result])

  function onPointerDown(e) {
    if (idx >= total || flying) return
    dragRef.current = { active: true, startX: e.clientX }
    e.target.setPointerCapture && e.target.setPointerCapture(e.pointerId)
  }
  function onPointerMove(e) {
    if (!dragRef.current.active) return
    setDragX(e.clientX - dragRef.current.startX)
  }
  function onPointerUp() {
    if (!dragRef.current.active) return
    dragRef.current.active = false
    if (dragX > 110) commit('correct')
    else if (dragX < -110) commit('wrong')
    else setDragX(0)
  }

  if (result === 'pass') {
    return (
      <div className="vrs-think vrs-think--choice vrs-fade-in" style={{ maxWidth: 600 }}>
        <span className="vrs-rule__ic" style={{ width: 64, height: 64, borderRadius: 16 }}>
          <Icon name="shield" size={30} />
        </span>
        <div>
          <div className="vrs-think__title">Verification passed</div>
          <div className="vrs-think__sub">
            You confirmed {verifiedCount} of {total} classifications with no errors. This
            source is verified — choose what happens next.
          </div>
        </div>
        <div className="vrs-next">
          <InteractiveCard className="vrs-next-option is-primary" onClick={onStop}>
            <span className="vrs-next-option__ic">
              <Icon name="check" size={20} />
            </span>
            <span className="vrs-next-option__body">
              <span className="vrs-next-option__t">
                Keep it verified
                <span className="vrs-next-tag">Recommended</span>
              </span>
              <span className="vrs-next-option__d">
                Save the verified source. You can route it to an exchange and backtest
                later, from the feed’s options.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </InteractiveCard>
          <InteractiveCard className="vrs-next-option" onClick={onPass}>
            <span className="vrs-next-option__ic">
              <Icon name="chart" size={20} />
            </span>
            <span className="vrs-next-option__body">
              <span className="vrs-next-option__t">Route &amp; backtest</span>
              <span className="vrs-next-option__d">
                Connect an exchange and simulate the source over its full history.
              </span>
            </span>
            <Icon name="arrowRight" size={18} />
          </InteractiveCard>
        </div>
      </div>
    )
  }
  if (result === 'loop') {
    return (
      <div className="vrs-think vrs-fade-in">
        <span
          className="vrs-rule__ic"
          style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'var(--pending-bg)',
            color: 'var(--pending-500)'
          }}
        >
          <Icon name="refresh" size={28} />
        </span>
        <div>
          <div className="vrs-think__title">{flaggedCount} flagged as wrong</div>
          <div className="vrs-think__sub">
            The ruleset isn’t tight enough yet. Label a few more messages so Verasig can
            refine the rules, then we’ll verify again.
          </div>
        </div>
        <Button
          variant="primary"
          size="lg"
          iconLeft={<Icon name="arrowLeft" size={16} />}
          onClick={onLoop}
        >
          Back to labelling
        </Button>
      </div>
    )
  }

  const loading = items === null
  const empty = !loading && total === 0
  const atEnd = !loading && !empty && idx >= total
  const current = !loading && !empty && !atEnd ? items[idx] : null
  const next1 = !loading && !empty && !atEnd ? items[idx + 1] : null

  function renderStage() {
    if (loading) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-dot-pulse" />
          <div className="vrs-rail__note">Loading classifications…</div>
        </div>
      )
    }
    if (empty) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="signals" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            Nothing to verify
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            There are no unreviewed classifications for this feed.
          </div>
        </div>
      )
    }
    if (atEnd) {
      return (
        <div className="vrs-card-bg" style={STAGE_CENTER}>
          <span className="vrs-rule__ic" style={{ width: 40, height: 40 }}>
            <Icon name="check" size={20} />
          </span>
          <div className="vrs-bf-title" style={{ fontSize: 'var(--text-lg)' }}>
            All classifications reviewed
          </div>
          <div className="vrs-rail__note" style={{ maxWidth: '26ch' }}>
            {verifiedCount} of {total} verified. Press{' '}
            <kbd className="vrs-kbd">↑</kbd> to revisit, or finish verification.
          </div>
        </div>
      )
    }
    return (
      <>
        {next1 && (
          <VerifyCard
            key={'bg' + next1.id}
            item={next1}
            isTop={false}
            style={{ transform: 'scale(0.95) translateY(14px)', opacity: 0.6 }}
          />
        )}
        <VerifyCard
          key={current.id}
          item={current}
          isTop={true}
          dragX={flying ? flying.dir * 600 : dragX}
          style={
            flying
              ? {
                  transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
                  transform: `translateX(${flying.dir * 600}px) rotate(${flying.dir * 18}deg)`
                }
              : dragRef.current.active
                ? {}
                : { transition: 'transform 0.25s var(--ease-out)' }
          }
        />
      </>
    )
  }

  return (
    <div className="vrs-label">
      <div className="vrs-deck">
        <div
          className="vrs-deck__stage"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{
            cursor: current ? (dragRef.current.active ? 'grabbing' : 'grab') : 'default'
          }}
        >
          {renderStage()}
        </div>

        <div className="vrs-swipe-controls">
          <IconButton
            variant="solid"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--no"
            label="Misclassified"
            onClick={() => commit('wrong')}
            disabled={atEnd || loading || empty}
            title="Misclassified (←)"
          >
            <Icon name="x" size={22} />
          </IconButton>
          <div className="vrs-deck__nav">
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Previous"
              onClick={goPrev}
              disabled={idx === 0}
              title="Previous (↑)"
            >
              <Icon name="arrowUp" size={18} />
            </IconButton>
            <IconButton
              variant="solid"
              className="vrs-swipe-key vrs-swipe-key--nav"
              label="Skip"
              onClick={goNext}
              disabled={atEnd || loading || empty}
              title="Skip (↓)"
            >
              <Icon name="arrowDown" size={18} />
            </IconButton>
          </div>
          <IconButton
            variant="accent"
            size="lg"
            className="vrs-swipe-key vrs-swipe-key--yes"
            label="Correct"
            onClick={() => commit('correct')}
            disabled={atEnd || loading || empty}
            title="Correct (→)"
          >
            <Icon name="check" size={22} />
          </IconButton>
        </div>
        <div className="vrs-deck__hint">
          <kbd>←</kbd> Misclassified &nbsp;·&nbsp; <kbd>→</kbd> Correct &nbsp;·&nbsp;{' '}
          <kbd>↑</kbd> Back &nbsp;·&nbsp; <kbd>↓</kbd> Skip
        </div>
      </div>

      <div className="vrs-rail">
        <div className="vrs-rail__h">Verify classification</div>
        <div className="vrs-rail__note">
          Verasig classified every message. Swipe right to confirm a call is correct,
          left to flag a misclassification. Any flag sends the rules back to refine.
        </div>

        <div className="vrs-rail__counts">
          <div className="vrs-count-card signal">
            <div className="vrs-count-card__v">{correctCount}</div>
            <div className="vrs-count-card__l">Correct</div>
          </div>
          <div className="vrs-count-card noise">
            <div className="vrs-count-card__v">{flaggedCount}</div>
            <div className="vrs-count-card__l">Flagged</div>
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Verified</span>
            <span>
              {verifiedCount} / {total}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${total ? (verifiedCount / total) * 100 : 0}%` }} />
          </div>
        </div>

        <div className="vrs-rail__progress">
          <div className="vrs-rail__plabel">
            <span>Minimum sample</span>
            <span>
              {Math.min(verifiedCount, VERIFY_MIN)} / {VERIFY_MIN}
            </span>
          </div>
          <div className="vrs-mini-track">
            <span style={{ width: `${Math.min(verifiedCount / VERIFY_MIN, 1) * 100}%` }} />
          </div>
        </div>

        <div className="vrs-rail__done">
          <Button
            variant="primary"
            fullWidth
            disabled={!minMet || submitting}
            loading={submitting}
            onClick={finish}
            iconLeft={<Icon name={flaggedCount > 0 ? 'refresh' : 'shield'} size={16} />}
          >
            {!minMet
              ? `Verify ${VERIFY_MIN - verifiedCount} more`
              : flaggedCount > 0
                ? 'Refine rules'
                : 'Finish verification'}
          </Button>
          <div className="vrs-rail__note" style={{ marginTop: 10, textAlign: 'center' }}>
            {!minMet
              ? `Confirm at least ${VERIFY_MIN} classifications to continue.`
              : flaggedCount > 0
                ? `${flaggedCount} flagged — we’ll refine the rules and re-verify.`
                : 'Keep going or finish — extra checks tighten confidence.'}
          </div>
        </div>
      </div>
    </div>
  )
}

const STAGE_CENTER = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  textAlign: 'center',
  padding: 30
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/VerifyView.test.jsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/features/pipeline/steps/VerifyView.jsx apps/frontend/web/src/features/pipeline/steps/VerifyView.test.jsx
git commit -m "feat(verify): fetch samples and submit verdicts to backend"
```

---

### Task 3.3: Wire VerifyView in ProductApp + verify

**Files:**
- Modify: `apps/frontend/web/src/app/ProductApp.jsx`

- [ ] **Step 1: Update the imports**

Extend the `pipelineApi` import in `ProductApp.jsx` to also include `getVerifySamples` and `submitVerify` (alphabetical order):
```js
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
```

- [ ] **Step 2: Replace the verify body**

Replace the existing `screen === 'verify'` block:
```jsx
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
```
with:
```jsx
    } else if (screen === 'verify') {
      body = (
        <VerifyView
          key={`verify-${verifyAttempt}`}
          chatId={activeChat.id}
          onGetSamples={(chatId) => getVerifySamples(authToken, chatId)}
          onSubmit={(chatId, verdicts) => submitVerify(authToken, chatId, verdicts)}
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
          onError={(tone, title, msg) => fireToast(tone, title, msg)}
        />
      )
    } else if (screen === 'exchange') {
```

- [ ] **Step 3: Lint + full suite**

Run: `cd apps/frontend && npm run lint --workspace verasig-web && make test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/app/ProductApp.jsx
git commit -m "feat(verify): wire VerifyView to backend samples and verdicts"
```

- [ ] **Step 5: Verify end-to-end**

With the stack running, complete Distill, then on Verify confirm: `GET /verify/samples` populates the deck with the backend `predicted` badge per card; verifying ≥6 and finishing calls `POST /verify`; a clean pass shows "Verification passed"; flagging any card and finishing shows "flagged as wrong" and **Back to labelling** loops to Label (which reloads counts including the verify-created labels). No console/network errors.

---

# Phase 4 — Deferred routing placeholder

### Task 4.1: PaidFeaturePlaceholder component

**Files:**
- Create: `apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.jsx`
- Create: `apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.test.jsx`:

```jsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PaidFeaturePlaceholder } from './PaidFeaturePlaceholder.jsx'

describe('PaidFeaturePlaceholder', () => {
  it('names the deferred feature and invokes onDone', () => {
    const onDone = vi.fn()
    render(<PaidFeaturePlaceholder feature="Exchange routing" onDone={onDone} />)

    expect(screen.getByText(/Exchange routing/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Back to feeds/i }))
    expect(onDone).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/PaidFeaturePlaceholder.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.jsx`:

```jsx
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

/* Verasig — upsell placeholder for the deferred post-verify routing chain
   (Exchange, Execution, Backtest). See ADR 0011. The real ExchangeView /
   ExecutionView / BacktestView are retained for the future paid-tier build. */
export function PaidFeaturePlaceholder({ feature, onDone }) {
  return (
    <div className="vrs-think vrs-think--choice vrs-fade-in" style={{ maxWidth: 560 }}>
      <span
        className="vrs-rule__ic"
        style={{ width: 64, height: 64, borderRadius: 16 }}
      >
        <Icon name="lock" size={28} />
      </span>
      <div>
        <div className="vrs-think__title">{feature} is a Pro feature</div>
        <div className="vrs-think__sub">
          Your source is verified and saved. Routing verified signals to an exchange,
          sizing execution, and backtesting are available on a higher plan — upgrade to
          unlock them.
        </div>
      </div>
      <Button
        variant="primary"
        size="lg"
        iconLeft={<Icon name="arrowLeft" size={16} />}
        onClick={onDone}
      >
        Back to feeds
      </Button>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/frontend/web && npx vitest run src/features/pipeline/steps/PaidFeaturePlaceholder.test.jsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.jsx apps/frontend/web/src/features/pipeline/steps/PaidFeaturePlaceholder.test.jsx
git commit -m "feat(pipeline): add paid-feature placeholder for deferred routing"
```

---

### Task 4.2: Mount the placeholder for exchange/risk/backtest screens

**Files:**
- Modify: `apps/frontend/web/src/app/ProductApp.jsx`

- [ ] **Step 1: Import the placeholder**

In `ProductApp.jsx`, add after the `BacktestView` import:
```js
import { PaidFeaturePlaceholder } from '../features/pipeline/steps/PaidFeaturePlaceholder.jsx'
```

- [ ] **Step 2: Replace the four deferred screen bodies**

Replace this block:
```jsx
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
```
with:
```jsx
    } else if (
      screen === 'exchange' ||
      screen === 'risk' ||
      screen === 'backtest' ||
      screen === 'backtest-result'
    ) {
      const featureName =
        screen === 'exchange' ? 'Exchange routing' : 'Backtesting'
      body = (
        <PaidFeaturePlaceholder
          feature={featureName}
          onDone={() => {
            void refreshSources().catch(() => {})
            exitToChats()
          }}
        />
      )
    }
```

- [ ] **Step 3: Remove now-unused imports**

`ExchangeView`, `ExecutionView`, and `BacktestView` are no longer referenced in `ProductApp.jsx`. Delete their three import lines so the lint passes (no-unused-vars):
```js
import { ExchangeView } from '../features/pipeline/steps/ExchangeView.jsx'
import { ExecutionView } from '../features/pipeline/steps/ExecutionView.jsx'
import { BacktestView } from '../features/pipeline/steps/BacktestView.jsx'
```
(The view files themselves stay in the repo — ADR 0011 keeps them for the paid-tier build.)

- [ ] **Step 4: Lint + full suite**

Run: `cd apps/frontend && npm run lint --workspace verasig-web && make test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cd apps/frontend && npm run format && cd ../..
git add apps/frontend/web/src/app/ProductApp.jsx
git commit -m "feat(pipeline): show upsell placeholder for deferred routing steps"
```

- [ ] **Step 6: Verify end-to-end**

With the stack running, pass Verify and choose "Route & backtest": confirm the placeholder renders, names the feature, and **Back to feeds** returns to the feed list with the source showing as verified (status refreshed from the backend). Walk the full flow once more — Backfill → Label → Distill → Verify → verified — with no console or network errors.

---

## Final verification

- [ ] `cd apps/frontend && make format-check && npm run lint --workspace verasig-web && make test` — all green.
- [ ] End-to-end against the real feed: Backfill → Label → Distill → Verify → verified, no errors.
- [ ] `git log --oneline` shows one focused commit per task; `ExchangesView.jsx` remains unstaged.
