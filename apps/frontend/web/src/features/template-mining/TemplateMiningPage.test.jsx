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
  return { groups, messages }
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
      expect(onLoadAudit).toHaveBeenCalledWith('apex', ['tpl_accept'])
    )

    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    // The accepted set did not change on the way to Verify — no second fetch.
    expect(onLoadAudit).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /Back to review/i }))
    expect(screen.getByRole('button', { name: /Continue to verify/i })).toBeTruthy()
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

  it('wires the audit gate to onFinish and onKeepVerified', async () => {
    const onFinish = vi.fn()
    const onKeepVerified = vi.fn()
    const { user } = await renderMinedPage({ onFinish, onKeepVerified })
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    await screen.findByRole('tab', { name: /Parsed/i })

    const review = screen.getByText('Review results').closest('.vrs-tm-review')
    await user.click(
      within(review).getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(onFinish).toHaveBeenCalledTimes(1)
    await user.click(within(review).getByRole('button', { name: /Keep verified/i }))
    expect(onKeepVerified).toHaveBeenCalledTimes(1)
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

// Reopening a verified feed should hydrate Verify from the backend's cached mine
// result instead of re-running the scan. onLoadMineResult resolves with the cached
// {groups, messages}; the live-mine job (onStartMine) must never be touched.
describe('TemplateMiningPage — resume from cached mine result', () => {
  it('hydrates the audit from the cache without re-running the scan', async () => {
    const { onStartMine, onStreamMine } = mineJobMocks()
    const { groups, messages } = mineResultFixture()
    const onLoadMineResult = vi.fn().mockResolvedValue({ groups, messages })
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
      expect(onLoadAudit).toHaveBeenCalledWith('7', [groups[0].templateKey])
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
    const { groups, messages } = mineResultFixture()
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
    act(() => stream.handlers.onDone({ groups, messages }))

    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
    expect(onBackToReview).not.toHaveBeenCalled()
  })

  it('falls back to Review when no confirmed templates come back', async () => {
    const { onStartMine, onStreamMine, stream } = mineJobMocks()
    const { groups, messages } = mineResultFixture()
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
    act(() => stream.handlers.onDone({ groups, messages }))

    await waitFor(() => expect(onBackToReview).toHaveBeenCalled())
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
  })
})
