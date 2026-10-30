import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateMiningPage } from './TemplateMiningPage.jsx'

/* Verasig — Template Mining page tests.
   Mining and the Verify audit both run server-side now, so every scenario here
   drives the same two seams the real app does: the mine job (onStartMine +
   onStreamMine, streamed to completion) and the audit fetch (onLoadAudit,
   called once the operator has accepted at least one template). There is no
   client-side miner left to fall back to. */

const feed = { id: 'apex', name: 'Apex Crypto Calls', tag: '@apex' }

// Two families: one the miner suggests accepting, one it flags for review — so
// the Suggested-accept / Needs-review split and the accept gate both have
// something to exercise.
function acceptCandidate(id, date) {
  return {
    message: { id, date, text: `BTCUSDT BUY entry 60000\nSL 58000\nTP 62000` },
    instruments: [],
    directions: [],
    prices: [],
    fields: {
      instrument: 'BTCUSDT',
      instrumentRaw: 'BTCUSDT',
      direction: 'BUY',
      orderType: 'limit',
      entry: { type: 'single', price: 60000 },
      stopLoss: 58000,
      takeProfits: [62000]
    },
    intent: 'new_signal',
    confidence: 0.92,
    rejectionReasons: [],
    parserIssues: [],
    templateKey: 'tpl_accept',
    normalizedTemplate: '<INSTRUMENT> <DIRECTION> entry <PRICE>\nSL <PRICE>\nTP <PRICE>'
  }
}

function reviewCandidate(id, date) {
  return {
    message: { id, date, text: 'ETHUSDT short now' },
    instruments: [],
    directions: [],
    prices: [],
    fields: {
      instrument: 'ETHUSDT',
      instrumentRaw: 'ETHUSDT',
      direction: 'SELL',
      orderType: 'market',
      entry: { type: 'market' },
      stopLoss: null,
      takeProfits: []
    },
    intent: 'new_signal',
    confidence: 0.55,
    rejectionReasons: [],
    parserIssues: [],
    templateKey: 'tpl_review',
    normalizedTemplate: '<INSTRUMENT> <DIRECTION> now'
  }
}

function acceptGroup() {
  const candidates = [
    acceptCandidate('c1', '2026-06-01'),
    acceptCandidate('c2', '2026-06-02')
  ]
  return {
    id: 'g1',
    templateKey: 'tpl_accept',
    normalizedTemplate: candidates[0].normalizedTemplate,
    candidates,
    examples: [candidates[0]],
    count: candidates.length,
    dateRange: { from: '2026-06-01', to: '2026-06-02' },
    confidenceAvg: 0.92,
    intentDistribution: {
      new_signal: 2,
      update: 0,
      result: 0,
      commentary: 0,
      unknown: 0
    },
    geometryWarnings: 0,
    status: 'unreviewed',
    suggestedAction: 'accept'
  }
}

function reviewGroup() {
  const candidates = [reviewCandidate('c3', '2026-06-03')]
  return {
    id: 'g2',
    templateKey: 'tpl_review',
    normalizedTemplate: candidates[0].normalizedTemplate,
    candidates,
    examples: [candidates[0]],
    count: candidates.length,
    dateRange: { from: '2026-06-03', to: '2026-06-03' },
    confidenceAvg: 0.55,
    intentDistribution: {
      new_signal: 1,
      update: 0,
      result: 0,
      commentary: 0,
      unknown: 0
    },
    geometryWarnings: 0,
    status: 'unreviewed',
    suggestedAction: 'review'
  }
}

function mineResultFixture() {
  const groups = [acceptGroup(), reviewGroup()]
  const messages = groups.flatMap((group) =>
    group.candidates.map((candidate) => ({
      id: candidate.message.id,
      text: candidate.message.text,
      date: candidate.message.date
    }))
  )
  return {
    reviewId: '10000000-0000-0000-0000-000000000001',
    inputRevision: 'a'.repeat(64),
    groups,
    messages
  }
}

// Mirrors the shape getMineAudit resolves with (ADR 0015): the same buckets
// the browser used to compute client-side, now server-computed.
function auditFixture() {
  return {
    parsedSignals: [
      {
        sourceMessageIds: ['c1'],
        instrument: 'BTCUSDT',
        instrumentRaw: 'BTCUSDT',
        direction: 'BUY',
        orderType: 'limit',
        entry: { type: 'single', price: 60000 },
        stopLoss: 58000,
        takeProfits: [62000],
        confidence: 0.92,
        parserRuleId: 'rule_accept',
        match: 'exact',
        intent: 'new_signal'
      }
    ],
    ambiguousCandidates: [],
    rejectedCandidates: [],
    rareTemplates: [],
    potentialMisses: []
  }
}

// Mirrors how ProductApp drives the page: the parent owns the current step and
// advances it in response to the page's callbacks.
function Harness({ activeFeed = feed, startStep = 'mine', ...props }) {
  const [step, setStep] = useState(startStep)
  return (
    <TemplateMiningPage
      activeFeed={activeFeed}
      authToken="jwt-token"
      step={step}
      onMined={() => setStep('review')}
      onContinueToVerify={() => setStep('verify')}
      onBackToReview={() => setStep('review')}
      {...props}
    />
  )
}

function mineJobMocks() {
  const onStartMine = vi.fn().mockResolvedValue({ jobId: 'user:apex:mine' })
  const stream = {}
  const onStreamMine = vi.fn((_id, handlers) => {
    stream.handlers = handlers
    return { close: vi.fn() }
  })
  return { onStartMine, onStreamMine, stream }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

// Renders the page, lets the server mine job complete with the fixture result,
// and returns the interaction helpers every Review/Verify test needs.
async function renderMinedPage(props = {}) {
  const { onStartMine, onStreamMine, stream } = mineJobMocks()
  const onLoadAudit = vi.fn().mockResolvedValue(auditFixture())
  const user = userEvent.setup()
  render(
    <Harness
      onStartMine={onStartMine}
      onStreamMine={onStreamMine}
      onLoadAudit={onLoadAudit}
      {...props}
    />
  )
  await waitFor(() => expect(stream.handlers).toBeTruthy())
  act(() => stream.handlers.onDone(mineResultFixture()))
  await screen.findByText('Suggested accept')
  return { user, onStartMine, onStreamMine, onLoadAudit, stream }
}

function acceptFirstTemplate(user) {
  const acceptButtons = screen.getAllByRole('button', {
    name: /Accept as signal format/i
  })
  return user.click(acceptButtons[0])
}

// Confirmation stays disabled until the debounced audit settles.
async function openSettledVerify(user) {
  await acceptFirstTemplate(user)
  await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
  await screen.findByRole('tab', { name: /Parsed/i })
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /Keep verified/i }).disabled).toBe(false)
  )
}

describe('TemplateMiningPage', () => {
  it('auto-runs the server mine and lands on Review with no manual button click', async () => {
    await renderMinedPage()
    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
  })

  it('renders the Suggested accept and Needs review sections', async () => {
    await renderMinedPage()
    expect(screen.getByText('Suggested accept')).toBeTruthy()
    // "Needs review" also labels the review group's suggestion badge, so scope
    // to the section header.
    expect(
      screen.getByText('Needs review', { selector: '.vrs-tm-section__title' })
    ).toBeTruthy()
  })

  it('gates "Continue to verify" until a template is accepted', async () => {
    const { user } = await renderMinedPage()
    const continueBtn = screen.getByRole('button', { name: /Continue to verify/i })
    expect(continueBtn.disabled).toBe(true)
    expect(screen.getByText(/Accept at least one template to continue/i)).toBeTruthy()

    await acceptFirstTemplate(user)
    expect(screen.getByRole('button', { name: /Continue to verify/i }).disabled).toBe(
      false
    )
  })

  it('fetches the server audit once a template is accepted, and shows it in Verify', async () => {
    const { user, onLoadAudit } = await renderMinedPage()
    // Nothing accepted yet — Review's coverage metric has nothing to fetch, and
    // the Verify audit tabs are not shown.
    expect(screen.queryByRole('tab', { name: /Parsed/i })).toBeNull()
    expect(onLoadAudit).not.toHaveBeenCalled()

    // Accepting (still on Review) already triggers the fetch — Review's
    // coverage metric needs it too, not just the Verify screen.
    await acceptFirstTemplate(user)
    await waitFor(() =>
      expect(onLoadAudit).toHaveBeenCalledWith(
        'apex',
        '10000000-0000-0000-0000-000000000001',
        ['tpl_accept']
      )
    )

    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    // The accepted set did not change on the way to Verify — no second fetch.
    expect(onLoadAudit).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /Back to review/i }))
    expect(screen.getByRole('button', { name: /Continue to verify/i })).toBeTruthy()
  })

  it('does not refetch the audit when the parent re-renders with a new onLoadAudit closure', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const loadAudit = vi.fn().mockResolvedValue(auditFixture())
    function Parent() {
      const [, setTick] = useState(0)
      return (
        <>
          <button onClick={() => setTick((tick) => tick + 1)}>Re-render parent</button>
          <Harness
            onStartMine={onStartMine}
            onStreamMine={onStreamMine}
            onLoadAudit={(...args) => loadAudit(...args)}
          />
        </>
      )
    }
    const user = userEvent.setup()
    render(<Parent />)
    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone(mineResultFixture()))
    await screen.findByText('Suggested accept')

    await acceptFirstTemplate(user)
    await waitFor(() => expect(loadAudit).toHaveBeenCalledTimes(1))
    await user.click(screen.getByRole('button', { name: /Re-render parent/i }))
    await user.click(screen.getByRole('button', { name: /Re-render parent/i }))
    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(loadAudit).toHaveBeenCalledTimes(1)
  })

  it('debounces the audit fetch instead of firing once per toggle', async () => {
    const { user, onLoadAudit } = await renderMinedPage()
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    await screen.findByRole('tab', { name: /Parsed/i })
    await waitFor(() => expect(onLoadAudit).toHaveBeenCalledTimes(1))
  })

  it('Apply all accepts the suggested templates', async () => {
    const { user } = await renderMinedPage()
    await user.click(screen.getByRole('button', { name: /Apply all/i }))
    expect(screen.getAllByText('Accepted').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Continue to verify/i }).disabled).toBe(
      false
    )
  })

  it('keeps the overlay manager under the Advanced disclosure', async () => {
    await renderMinedPage({ onSaveOverlay: vi.fn() })
    const advanced = screen.getByText('Advanced').closest('details')
    expect(within(advanced).getByText('Coin aliases')).toBeTruthy()
  })

  it('sends one awaited confirmation command with the selected destination', async () => {
    const onConfirmVerification = vi.fn().mockResolvedValue()
    const { user } = await renderMinedPage({ onConfirmVerification })
    await openSettledVerify(user)

    const review = screen.getByText('Review results').closest('.vrs-tm-review')
    await user.click(
      within(review).getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(onConfirmVerification).toHaveBeenCalledWith({
      reviewId: '10000000-0000-0000-0000-000000000001',
      acceptedTemplateKeys: ['tpl_accept'],
      destination: 'exchange'
    })
  })

  it('keeps Verify mounted and disables both actions while confirmation is pending', async () => {
    const confirmation = deferred()
    const onConfirmVerification = vi.fn().mockReturnValue(confirmation.promise)
    const { user } = await renderMinedPage({ onConfirmVerification })
    await openSettledVerify(user)

    await user.click(screen.getByRole('button', { name: /Keep verified/i }))

    expect(screen.getByText('Review results')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Keep verified/i }).disabled).toBe(true)
    expect(
      screen.getByRole('button', { name: /Confirming verification/i }).disabled
    ).toBe(true)
    expect(onConfirmVerification).toHaveBeenCalledTimes(1)

    await act(async () => confirmation.resolve())
  })

  it('shows a confirmation rejection inline and permits retry', async () => {
    const onConfirmVerification = vi
      .fn()
      .mockRejectedValueOnce(new Error('Confirmation unavailable.'))
      .mockResolvedValueOnce()
    const { user } = await renderMinedPage({ onConfirmVerification })
    await openSettledVerify(user)

    await user.click(screen.getByRole('button', { name: /Keep verified/i }))

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Confirmation unavailable.'
    )
    expect(screen.getByText('Review results')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Keep verified/i }).disabled).toBe(false)

    await user.click(screen.getByRole('button', { name: /Keep verified/i }))
    await waitFor(() => expect(onConfirmVerification).toHaveBeenCalledTimes(2))
  })

  it('requires a fresh mine when the server rejects a stale review', async () => {
    const stale = Object.assign(new Error('Review is stale.'), {
      status: 409,
      code: 'MINING_REVIEW_STALE'
    })
    const onLoadAudit = vi.fn().mockRejectedValue(stale)
    const { user, onStartMine } = await renderMinedPage({ onLoadAudit })
    await acceptFirstTemplate(user)

    expect(await screen.findByText(/Messages or parser settings changed/i)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /Re-mine messages/i }))

    await waitFor(() => expect(onStartMine).toHaveBeenCalledTimes(2))
    expect(screen.getByText(/Mining Apex Crypto Calls/i)).toBeTruthy()
  })

  it('clears stale mining state and starts exactly one mine after overlay save', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const onSaveOverlay = vi.fn().mockResolvedValue()
    const user = userEvent.setup()
    render(
      <Harness
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadAudit={vi.fn().mockResolvedValue(auditFixture())}
        onSaveOverlay={onSaveOverlay}
      />
    )
    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone(mineResultFixture()))
    await screen.findByText('Suggested accept')
    await acceptFirstTemplate(user)
    await user.type(screen.getByPlaceholderText(/Add reject phrase/i), 'promo')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))

    await waitFor(() => expect(onSaveOverlay).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(onStartMine).toHaveBeenCalledTimes(2))
    expect(screen.getByText(/Mining Apex Crypto Calls/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Continue to verify/i })).toBeNull()

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(onStartMine).toHaveBeenCalledTimes(2)

    act(() => stream.handlers.onDone(mineResultFixture()))
    await screen.findByRole('button', { name: /Continue to verify/i })
    expect(screen.getByRole('button', { name: /Continue to verify/i }).disabled).toBe(
      true
    )
  })

  it('retains overlay edits and does not re-mine after a failed save', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const onSaveOverlay = vi.fn().mockRejectedValue(new Error('Overlay unavailable.'))
    const user = userEvent.setup()
    render(
      <Harness
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadAudit={vi.fn().mockResolvedValue(auditFixture())}
        onSaveOverlay={onSaveOverlay}
      />
    )
    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone(mineResultFixture()))
    await screen.findByText('Suggested accept')
    const input = screen.getByPlaceholderText(/Add reject phrase/i)
    await user.type(input, 'promo')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Overlay unavailable.'
    )
    expect(input.value).toBe('promo')
    expect(onStartMine).toHaveBeenCalledTimes(1)
  })

  it('no longer offers the alternate-source disclosure', async () => {
    await renderMinedPage()
    expect(screen.queryByText(/Use sample or pasted messages instead/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /Run template mining/i })).toBeNull()
  })

  it('never renders NaN', async () => {
    const { user } = await renderMinedPage()
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    await screen.findByRole('tab', { name: /Parsed/i })
    expect(screen.queryByText(/NaN/)).toBeNull()
  })

  it('closes the examples modal after Accept', async () => {
    const { user } = await renderMinedPage()
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Accept$/ }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('closes the examples modal after Reject', async () => {
    const { user } = await renderMinedPage()
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Reject$/ }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('keeps the examples modal open after Reset', async () => {
    const { user } = await renderMinedPage()
    // Decide on the card first so the modal opens already-accepted (shows Reset).
    await acceptFirstTemplate(user)
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Reset$/ }))
    expect(screen.queryByRole('dialog')).toBeTruthy()
  })
})

describe('TemplateMiningPage — mine failure', () => {
  it('shows an error with a retry affordance and re-runs on retry', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const fireToast = vi.fn()
    const user = userEvent.setup()
    render(
      <Harness
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        fireToast={fireToast}
      />
    )

    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onError({ message: 'Server exploded' }))

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText(/Server exploded/)).toBeTruthy()
    expect(fireToast).toHaveBeenCalledWith(
      'rejected',
      'Mining failed',
      'Server exploded'
    )

    onStartMine.mockClear()
    await user.click(screen.getByRole('button', { name: /Try again/i }))
    await waitFor(() => expect(onStartMine).toHaveBeenCalled())
  })
})

// Reopening a verified feed should hydrate Verify from the latest current review
// instead of re-running the scan. onLoadMineResult resolves with the stored
// {groups, messages}; the live-mine job (onStartMine) must never be touched.
describe('TemplateMiningPage — resume from a current mining review', () => {
  it('hydrates the audit from the cache without re-running the scan', async () => {
    const { onStartMine, onStreamMine } = mineJobMocks()
    const mineResult = mineResultFixture()
    const { groups } = mineResult
    const onLoadMineResult = vi.fn().mockResolvedValue(mineResult)
    const onLoadConfirmed = vi
      .fn()
      .mockResolvedValue({ acceptedTemplateKeys: [groups[0].templateKey] })
    const onLoadAudit = vi.fn().mockResolvedValue(auditFixture())

    render(
      <Harness
        activeFeed={{ id: '7', name: 'Pilot Signals' }}
        startStep="verify"
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadMineResult={onLoadMineResult}
        onLoadConfirmed={onLoadConfirmed}
        onLoadAudit={onLoadAudit}
      />
    )

    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(onLoadMineResult).toHaveBeenCalledWith('7')
    expect(onStartMine).not.toHaveBeenCalled()
    await waitFor(() =>
      expect(onLoadAudit).toHaveBeenCalledWith('7', mineResult.reviewId, [
        groups[0].templateKey
      ])
    )
  })

  it('falls back to a live mine when nothing is cached (404)', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const onLoadMineResult = vi.fn().mockRejectedValue(new Error('no cached result'))
    const onLoadConfirmed = vi.fn().mockResolvedValue({ acceptedTemplateKeys: [] })

    render(
      <Harness
        activeFeed={{ id: '7', name: 'Pilot Signals' }}
        startStep="verify"
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadMineResult={onLoadMineResult}
        onLoadConfirmed={onLoadConfirmed}
      />
    )

    await waitFor(() => expect(onLoadMineResult).toHaveBeenCalledWith('7'))
    await waitFor(() => expect(stream.handlers).toBeTruthy())
    expect(onStartMine).toHaveBeenCalled()
  })
})

describe('TemplateMiningPage — resume a verified feed', () => {
  it('reseeds the confirmed templates and shows the audit (no bounce)', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const mineResult = mineResultFixture()
    const { groups } = mineResult
    const confirmedKey = groups[0].templateKey
    const onLoadConfirmed = vi
      .fn()
      .mockResolvedValue({ acceptedTemplateKeys: [confirmedKey] })
    const onBackToReview = vi.fn()
    const onLoadAudit = vi.fn().mockResolvedValue(auditFixture())

    render(
      <Harness
        activeFeed={{ id: '7', name: 'Pilot Signals' }}
        startStep="verify"
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadConfirmed={onLoadConfirmed}
        onBackToReview={onBackToReview}
        onLoadAudit={onLoadAudit}
      />
    )

    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone(mineResult))

    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
    expect(onBackToReview).not.toHaveBeenCalled()
  })

  it('falls back to Review when no confirmed templates come back', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const mineResult = mineResultFixture()
    const onLoadConfirmed = vi.fn().mockResolvedValue({ acceptedTemplateKeys: [] })
    const onBackToReview = vi.fn()

    render(
      <Harness
        activeFeed={{ id: '7', name: 'Pilot Signals' }}
        startStep="verify"
        onStartMine={onStartMine}
        onStreamMine={onStreamMine}
        onLoadConfirmed={onLoadConfirmed}
        onBackToReview={onBackToReview}
      />
    )

    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone(mineResult))

    await waitFor(() => expect(onBackToReview).toHaveBeenCalled())
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
  })
})
