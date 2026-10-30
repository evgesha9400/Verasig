import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuditReview } from './AuditReview.jsx'

/* The review surface: tabs across the five audit buckets, a free-text search,
   a filter-by-template Select, and a paginated list of the active bucket. */

function parsedSignal(i, ruleId) {
  const instrument = i === 30 ? 'AAVEUSDT' : `SYM${i}USDT`
  return {
    sourceMessageIds: [`m${i}`],
    instrument,
    instrumentRaw: instrument,
    direction: 'SELL',
    orderType: 'limit',
    entry: { type: 'single', price: 100 + i },
    stopLoss: 200 + i,
    takeProfits: [50 + i],
    confidence: 0.87,
    parserRuleId: ruleId,
    intent: 'new_signal'
  }
}

// 30 parsed signals: 1–20 from rule_a, 21–30 from rule_b (incl. AAVEUSDT at #30).
const PARSED = Array.from({ length: 30 }, (_, idx) => {
  const i = idx + 1
  return parsedSignal(i, i <= 20 ? 'rule_a' : 'rule_b')
})

const MESSAGES = PARSED.map((s, idx) => ({
  id: `m${idx + 1}`,
  text: idx + 1 === 5 ? 'note zebraword here' : `Монета ${s.instrument}`
}))

const RULES = [
  {
    id: 'rule_a',
    name: 'Limit signal · direction + entry + SL + TP',
    templateKey: 'tpl_a'
  },
  { id: 'rule_b', name: 'Market signal · direction', templateKey: 'tpl_b' }
]

const AUDIT = {
  parsedSignals: PARSED,
  ambiguousCandidates: [
    {
      message: { id: 'c1', text: 'ambiguous candidate one' },
      intent: 'new_signal',
      confidence: 0.4,
      templateKey: 'tpl_a',
      fields: {
        instrument: 'ARBUSDT',
        direction: 'BUY',
        orderType: 'limit',
        entry: { type: 'single', price: 0.3853 },
        stopLoss: 0.3853,
        takeProfits: [0.3901]
      },
      rejectionReasons: ['Stop loss should sit below entry for a LONG.'],
      parserIssues: [
        {
          code: 'stop_loss_on_wrong_side',
          field: 'stopLoss',
          label: 'Stop loss equals entry',
          message: 'Stop loss should sit below entry for a LONG.',
          price: 0.3853
        }
      ]
    }
  ],
  rejectedCandidates: [
    { message: { id: 'r1', text: 'closed in profit' }, intent: 'result' }
  ],
  rareTemplates: [
    { templateKey: 'tpl_z', normalizedTemplate: 'BUY <INSTRUMENT>', count: 2 }
  ],
  potentialMisses: [{ id: 'p1', text: 'chart review for LTC' }]
}

function renderReview(extraProps = {}) {
  return render(
    <AuditReview
      audit={AUDIT}
      messages={MESSAGES}
      templates={RULES}
      hasAccepted={true}
      {...extraProps}
    />
  )
}

describe('AuditReview', () => {
  it('shows a tab per bucket with counts and lists the parsed signals first', () => {
    renderReview()
    expect(screen.getByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Ambiguous/i })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Rejected/i })).toBeTruthy()
    // Parsed is the default tab; first page shows parsed rows.
    expect(screen.getByText(/SYM1USDT SELL/)).toBeTruthy()
  })

  it('paginates the parsed list 25 per page', async () => {
    const user = userEvent.setup()
    renderReview()
    // Page 1: signal 1 visible, signal 30 (AAVEUSDT, page 2) not yet.
    expect(screen.getByText(/1\s*[–-]\s*25 of 30/)).toBeTruthy()
    expect(screen.queryByText(/AAVEUSDT SELL/)).toBeNull()

    await user.click(screen.getByRole('button', { name: /Next/i }))

    expect(screen.getByText(/26\s*[–-]\s*30 of 30/)).toBeTruthy()
    expect(screen.getByText(/AAVEUSDT SELL/)).toBeTruthy()
    expect(screen.queryByText(/SYM1USDT SELL/)).toBeNull()
  })

  it('caps the observer parsed bucket to 200 and shows the notice', async () => {
    const many = Array.from({ length: 205 }, (_, idx) =>
      parsedSignal(idx + 1, 'rule_a')
    )
    const messages = many.map((s, idx) => ({
      id: `m${idx + 1}`,
      text: `Монета ${s.instrument}`
    }))
    const onUpgrade = vi.fn()
    render(
      <AuditReview
        audit={{ ...AUDIT, parsedSignals: many }}
        messages={messages}
        templates={RULES}
        hasAccepted
        plan="observer"
        onUpgrade={onUpgrade}
      />
    )

    expect(screen.getByText(/200 most recent of 205 detected signals/)).toBeTruthy()
    // Pager total reflects the capped set, not the full 205.
    expect(screen.getByText(/1\s*[–-]\s*25 of 200/)).toBeTruthy()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Upgrade' }))
    expect(onUpgrade).toHaveBeenCalledTimes(1)
  })

  it('does not cap or show the notice for a paid plan', () => {
    renderReview({ plan: 'operator' })
    expect(screen.queryByText(/most recent of/)).toBeNull()
    expect(screen.getByText(/1\s*[–-]\s*25 of 30/)).toBeTruthy()
  })

  it('search filters across the whole bucket, not just the visible page', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.type(screen.getByPlaceholderText(/Search results/i), 'AAVE')

    // AAVEUSDT lived on page 2 but search spans the full set and resets to page 1.
    expect(screen.getByText(/AAVEUSDT SELL/)).toBeTruthy()
    expect(screen.queryByText(/SYM1USDT SELL/)).toBeNull()
  })

  it('search also matches a parsed signal by its source message text', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.type(screen.getByPlaceholderText(/Search results/i), 'zebraword')
    // Signal #5 (SYM5USDT) has the unique word only in its source message text.
    expect(screen.getByText(/SYM5USDT SELL/)).toBeTruthy()
    expect(screen.queryByText(/SYM1USDT SELL/)).toBeNull()
  })

  it('disambiguates same-named templates by their parsed count', () => {
    renderReview()
    // rule_a parsed 20 signals (1–20), rule_b parsed 10 (21–30).
    const options = [...screen.getByRole('combobox').options].map((o) => o.textContent)
    expect(options.some((label) => /· 20 parsed/.test(label))).toBe(true)
    expect(options.some((label) => /· 10 parsed/.test(label))).toBe(true)
  })

  it('filters parsed rows by the selected template', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.selectOptions(screen.getByRole('combobox'), 'rule_b')

    // rule_b = signals 21–30 (incl. AAVEUSDT); rule_a signals drop out.
    expect(screen.getByText(/AAVEUSDT SELL/)).toBeTruthy()
    expect(screen.queryByText(/SYM1USDT SELL/)).toBeNull()
  })

  it('disables the template Select on a bucket with no template link', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.click(screen.getByRole('tab', { name: /Rejected/i }))

    expect(screen.getByRole('combobox').disabled).toBe(true)
    expect(screen.getByText(/closed in profit/)).toBeTruthy()
  })

  it('keeps rows collapsed by default — the original message is hidden', () => {
    renderReview()
    // The parsed one-line summary is shown; the full source message is not.
    expect(screen.getByText(/SYM1USDT SELL/)).toBeTruthy()
    expect(screen.queryByText(/Монета SYM1USDT/)).toBeNull()
  })

  it('expands a parsed row to show the original message and parsed fields', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.click(screen.getByRole('button', { name: /SYM1USDT SELL/ }))
    // Original message (left) and a parsed-fields table (right) appear.
    expect(screen.getByText(/Монета SYM1USDT/)).toBeTruthy()
    expect(screen.getByText('Stop loss')).toBeTruthy()
  })

  it('expands every visible row via the Expand all checkbox', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.click(screen.getByRole('checkbox', { name: /Expand all/i }))
    expect(screen.getByText(/Монета SYM1USDT/)).toBeTruthy()
    expect(screen.getByText(/Монета SYM2USDT/)).toBeTruthy()
  })

  it('shows an empty state when filters match nothing', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.type(screen.getByPlaceholderText(/Search results/i), 'zzznomatch')
    expect(screen.getByText(/No results match/i)).toBeTruthy()
  })

  it('shows the loader (not the empty state) while the audit is loading', () => {
    // An empty audit + loading=true must read as "refreshing", never "no results".
    render(
      <AuditReview
        audit={{
          parsedSignals: [],
          ambiguousCandidates: [],
          rejectedCandidates: [],
          rareTemplates: [],
          potentialMisses: []
        }}
        messages={[]}
        templates={RULES}
        hasAccepted={true}
        loading={true}
      />
    )
    expect(screen.getByText('Refreshing the audit…')).toBeTruthy()
    expect(screen.queryByText(/No results match/i)).toBeNull()
  })

  it('shows the empty state (not the loader) once loading finishes with no rows', () => {
    render(
      <AuditReview
        audit={{
          parsedSignals: [],
          ambiguousCandidates: [],
          rejectedCandidates: [],
          rareTemplates: [],
          potentialMisses: []
        }}
        messages={[]}
        templates={RULES}
        hasAccepted={true}
        loading={false}
      />
    )
    expect(screen.getByText(/No results match/i)).toBeTruthy()
    expect(screen.queryByText('Refreshing the audit…')).toBeNull()
  })

  it('labels ambiguous price-geometry issues and highlights the bad field', async () => {
    const user = userEvent.setup()
    const { container } = renderReview()

    await user.click(screen.getByRole('tab', { name: /Ambiguous/i }))

    expect(screen.getByText(/Price geometry issue/i)).toBeTruthy()
    expect(screen.getByText(/Stop loss equals entry/i)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: /ambiguous candidate one/i }))

    expect(container.querySelector('[data-field="stopLoss"].is-warning')).toBeTruthy()
    expect(
      screen.getByText(/Stop loss should sit below entry for a LONG/i)
    ).toBeTruthy()
  })

  it('orders parsed rows within one family by confidence, highest first', () => {
    // Same rule → coverage ties → the confidence tiebreak surfaces the strongest
    // extraction first (input order is low-then-high).
    const audit = {
      parsedSignals: [
        {
          sourceMessageIds: ['lo'],
          instrument: 'LOWUSDT',
          direction: 'SELL',
          orderType: 'limit',
          entry: null,
          stopLoss: null,
          takeProfits: [],
          confidence: 0.55,
          parserRuleId: 'rule_a',
          intent: 'new_signal'
        },
        {
          sourceMessageIds: ['hi'],
          instrument: 'HIGHUSDT',
          direction: 'BUY',
          orderType: 'limit',
          entry: null,
          stopLoss: null,
          takeProfits: [],
          confidence: 0.95,
          parserRuleId: 'rule_a',
          intent: 'new_signal'
        }
      ],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const { container } = render(
      <AuditReview audit={audit} messages={[]} templates={RULES} hasAccepted={true} />
    )
    const texts = [...container.querySelectorAll('.vrs-tm-review__row-text')].map(
      (node) => node.textContent
    )
    const high = texts.findIndex((text) => /HIGHUSDT/.test(text))
    const low = texts.findIndex((text) => /LOWUSDT/.test(text))
    expect(high).toBe(0)
    expect(low).toBeGreaterThan(high)
  })

  it('groups parsed rows by template coverage — the biggest family first', () => {
    // The most-covering template's signals lead, even when a smaller family has a
    // higher-confidence signal. This is the visible "most-likely template first".
    const sig = (id, instrument, ruleId, confidence) => ({
      sourceMessageIds: [id],
      instrument,
      direction: 'BUY',
      orderType: 'limit',
      entry: null,
      stopLoss: null,
      takeProfits: [],
      confidence,
      parserRuleId: ruleId,
      intent: 'new_signal',
      match: 'exact'
    })
    const audit = {
      parsedSignals: [
        sig('s1', 'ZZZUSDT', 'rule_b', 0.99), // small family, highest confidence
        sig('b1', 'AAAUSDT', 'rule_a', 0.6),
        sig('b2', 'BBBUSDT', 'rule_a', 0.6) // big family (2 signals), lower confidence
      ],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const { container } = render(
      <AuditReview audit={audit} messages={[]} templates={RULES} hasAccepted={true} />
    )
    const texts = [...container.querySelectorAll('.vrs-tm-review__row-text')].map(
      (node) => node.textContent
    )
    const bigFamily = texts.findIndex((text) => /AAAUSDT/.test(text))
    const smallFamily = texts.findIndex((text) => /ZZZUSDT/.test(text))
    // Big family (more coverage) leads despite the small family's higher confidence.
    expect(smallFamily).toBeGreaterThan(bigFamily)
    expect(smallFamily).toBe(2)
  })

  it('orders ambiguous rows by template coverage, then confidence', async () => {
    // Same two-field order as the parsed tab: the candidate whose template parsed
    // more messages leads, even when a smaller-template candidate is more confident.
    const user = userEvent.setup()
    const parsed = (id, ruleId) => ({
      sourceMessageIds: [id],
      instrument: 'X',
      direction: 'BUY',
      orderType: 'limit',
      entry: null,
      stopLoss: null,
      takeProfits: [],
      confidence: 0.8,
      parserRuleId: ruleId,
      intent: 'new_signal',
      match: 'exact'
    })
    const candidate = (id, text, templateKey, confidence) => ({
      message: { id, text },
      intent: 'new_signal',
      confidence,
      templateKey,
      fields: {},
      rejectionReasons: [],
      parserIssues: []
    })
    const audit = {
      // rule_big parsed 2, rule_small parsed 1 → rule_big has more coverage.
      parsedSignals: [
        parsed('p1', 'rule_big'),
        parsed('p2', 'rule_big'),
        parsed('p3', 'rule_small')
      ],
      ambiguousCandidates: [
        candidate('c1', 'small template high confidence', 'tpl_small', 0.99),
        candidate('c2', 'big template low confidence', 'tpl_big', 0.5)
      ],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const rules = [
      { id: 'rule_big', name: 'Big', templateKey: 'tpl_big' },
      { id: 'rule_small', name: 'Small', templateKey: 'tpl_small' }
    ]
    const { container } = render(
      <AuditReview audit={audit} messages={[]} templates={rules} hasAccepted={true} />
    )
    await user.click(screen.getByRole('tab', { name: /Ambiguous/i }))
    const texts = [...container.querySelectorAll('.vrs-tm-review__row-text')].map(
      (node) => node.textContent
    )
    const big = texts.findIndex((text) => /big template/.test(text))
    const small = texts.findIndex((text) => /small template/.test(text))
    expect(big).toBeLessThan(small)
  })

  it('orders parsed rows newest-first when coverage and confidence tie', () => {
    // Same family, same confidence → the source-message date is the only signal,
    // so the newest message leads.
    const sig = (id, instrument) => ({
      sourceMessageIds: [id],
      instrument,
      direction: 'BUY',
      orderType: 'limit',
      entry: null,
      stopLoss: null,
      takeProfits: [],
      confidence: 0.8,
      parserRuleId: 'rule_a',
      intent: 'new_signal',
      match: 'exact'
    })
    const audit = {
      parsedSignals: [sig('old', 'OLDUSDT'), sig('new', 'NEWUSDT')],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const messages = [
      { id: 'old', text: 'older', date: '2026-06-01T00:00:00Z' },
      { id: 'new', text: 'newer', date: '2026-06-05T00:00:00Z' }
    ]
    const { container } = render(
      <AuditReview
        audit={audit}
        messages={messages}
        templates={RULES}
        hasAccepted={true}
      />
    )
    const texts = [...container.querySelectorAll('.vrs-tm-review__row-text')].map(
      (node) => node.textContent
    )
    const newIdx = texts.findIndex((text) => /NEWUSDT/.test(text))
    const oldIdx = texts.findIndex((text) => /OLDUSDT/.test(text))
    expect(newIdx).toBeLessThan(oldIdx)
  })

  it('shows the reformatted source-message date when a parsed row is expanded', async () => {
    const user = userEvent.setup()
    const audit = {
      parsedSignals: [
        {
          sourceMessageIds: ['m1'],
          instrument: 'BTCUSDT',
          direction: 'BUY',
          orderType: 'limit',
          entry: null,
          stopLoss: null,
          takeProfits: [],
          confidence: 0.8,
          parserRuleId: 'rule_a',
          intent: 'new_signal',
          match: 'exact'
        }
      ],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const messages = [{ id: 'm1', text: 'the original', date: '2026-06-01T08:42:00Z' }]
    const { container } = render(
      <AuditReview
        audit={audit}
        messages={messages}
        templates={RULES}
        hasAccepted={true}
      />
    )
    await user.click(screen.getByRole('button', { name: /BTCUSDT BUY/ }))
    const date = container.querySelector('.vrs-tm-ex__date')
    expect(date).toBeTruthy()
    expect(date.textContent).toContain('2026')
  })

  it('orders rejected rows newest-first and shows the date on expand', async () => {
    const user = userEvent.setup()
    const audit = {
      parsedSignals: [],
      ambiguousCandidates: [],
      rejectedCandidates: [
        {
          message: { id: 'r_old', text: 'old rejected', date: '2026-06-01T00:00:00Z' },
          intent: 'result'
        },
        {
          message: { id: 'r_new', text: 'new rejected', date: '2026-06-09T00:00:00Z' },
          intent: 'result'
        }
      ],
      rareTemplates: [],
      potentialMisses: []
    }
    const { container } = render(
      <AuditReview audit={audit} messages={[]} templates={RULES} hasAccepted={true} />
    )
    await user.click(screen.getByRole('tab', { name: /Rejected/i }))
    const texts = [...container.querySelectorAll('.vrs-tm-review__row-text')].map(
      (node) => node.textContent
    )
    const newIdx = texts.findIndex((text) => /new rejected/.test(text))
    const oldIdx = texts.findIndex((text) => /old rejected/.test(text))
    expect(newIdx).toBeLessThan(oldIdx)

    await user.click(screen.getByRole('button', { name: /new rejected/i }))
    const date = container.querySelector('.vrs-tm-ex__date')
    expect(date.textContent).toContain('2026')
  })

  it('badges a fallback-captured parsed row, but not an exact one', () => {
    const signal = (id, instrument, confidence, match) => ({
      sourceMessageIds: [id],
      instrument,
      direction: 'BUY',
      orderType: 'limit',
      entry: null,
      stopLoss: null,
      takeProfits: [],
      confidence,
      parserRuleId: 'rule_a',
      intent: 'new_signal',
      match
    })
    const audit = {
      parsedSignals: [
        signal('e', 'BBBUSDT', 0.9, 'exact'),
        signal('f', 'AAAUSDT', 0.8, 'fallback')
      ],
      ambiguousCandidates: [],
      rejectedCandidates: [],
      rareTemplates: [],
      potentialMisses: []
    }
    const { container } = render(
      <AuditReview audit={audit} messages={[]} templates={RULES} hasAccepted={true} />
    )
    const rows = [...container.querySelectorAll('.vrs-tm-review__item')]
    const fallbackRow = rows.find((r) => /AAAUSDT/.test(r.textContent))
    const exactRow = rows.find((r) => /BBBUSDT/.test(r.textContent))
    expect(fallbackRow.textContent).toMatch(/fallback/i)
    expect(exactRow.textContent).not.toMatch(/fallback/i)
  })

  it('prompts to accept a family when nothing is accepted yet', () => {
    render(
      <AuditReview audit={AUDIT} messages={[]} templates={[]} hasAccepted={false} />
    )
    expect(screen.getByText(/Accept at least one template family/i)).toBeTruthy()
    expect(screen.queryByRole('tab', { name: /Parsed/i })).toBeNull()
  })

  it('renders no gate buttons in the empty state, even when handlers are passed', () => {
    render(
      <AuditReview
        audit={AUDIT}
        messages={[]}
        templates={[]}
        hasAccepted={false}
        onFinish={vi.fn()}
        onKeepVerified={vi.fn()}
      />
    )
    expect(
      screen.queryByRole('button', { name: /Confirm & route to Exchange/i })
    ).toBeNull()
    expect(screen.queryByRole('button', { name: /Keep verified/i })).toBeNull()
  })

  it('always renders "Confirm & route to Exchange" once accepted, and calls onFinish', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()
    renderReview({ onFinish })
    await user.click(
      screen.getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(onFinish).toHaveBeenCalledTimes(1)
  })

  it('renders "Keep verified" only when onKeepVerified is provided, and calls it', async () => {
    const user = userEvent.setup()
    const onKeepVerified = vi.fn()
    renderReview({ onKeepVerified })
    const keepButton = screen.getByRole('button', { name: /Keep verified/i })
    await user.click(keepButton)
    expect(onKeepVerified).toHaveBeenCalledTimes(1)
  })

  it('omits "Keep verified" when onKeepVerified is not provided', () => {
    renderReview()
    expect(screen.queryByRole('button', { name: /Keep verified/i })).toBeNull()
  })

  it('renders no errors when neither onFinish nor onKeepVerified is passed', async () => {
    const user = userEvent.setup()
    renderReview()
    await user.click(
      screen.getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(screen.queryByRole('button', { name: /Keep verified/i })).toBeNull()
  })

  it('disables both confirmation actions and shows progress while pending', () => {
    renderReview({
      onFinish: vi.fn(),
      onKeepVerified: vi.fn(),
      confirmationPending: true
    })

    expect(
      screen.getByRole('button', { name: /Confirming verification/i }).disabled
    ).toBe(true)
    expect(screen.getByRole('button', { name: /Keep verified/i }).disabled).toBe(true)
  })

  it.each([
    ['loading', { loading: true }],
    ['failed', { error: 'Audit unavailable.' }]
  ])('disables both confirmation actions while the audit is %s', (_, props) => {
    renderReview({ onFinish: vi.fn(), onKeepVerified: vi.fn(), ...props })

    expect(
      screen.getByRole('button', { name: /Confirm & route to Exchange/i }).disabled
    ).toBe(true)
    expect(screen.getByRole('button', { name: /Keep verified/i }).disabled).toBe(true)
  })

  it('renders a retryable confirmation failure inline', () => {
    renderReview({
      onFinish: vi.fn(),
      confirmationError: 'Confirmation unavailable.'
    })

    expect(screen.getByRole('alert').textContent).toContain('Confirmation unavailable.')
    expect(
      screen.getByRole('button', { name: /Confirm & route to Exchange/i }).disabled
    ).toBe(false)
  })
})
