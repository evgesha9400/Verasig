import { describe, expect, it } from 'vitest'
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

function renderReview() {
  return render(
    <AuditReview audit={AUDIT} messages={MESSAGES} rules={RULES} hasAccepted={true} />
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

  it('labels ambiguous price-geometry issues and highlights the bad field', async () => {
    const user = userEvent.setup()
    const { container } = renderReview()

    await user.click(screen.getByRole('tab', { name: /Ambiguous/i }))

    expect(screen.getByText(/Price geometry issue/i)).toBeTruthy()
    expect(screen.getByText(/Stop loss equals entry/i)).toBeTruthy()

    await user.click(screen.getByRole('button', { name: /ambiguous candidate one/i }))

    expect(container.querySelector('[data-field="stopLoss"].is-warning')).toBeTruthy()
    expect(screen.getByText(/Stop loss should sit below entry for a LONG/i)).toBeTruthy()
  })

  it('prompts to accept a family when nothing is accepted yet', () => {
    render(<AuditReview audit={AUDIT} messages={[]} rules={[]} hasAccepted={false} />)
    expect(screen.getByText(/Accept at least one template family/i)).toBeTruthy()
    expect(screen.queryByRole('tab', { name: /Parsed/i })).toBeNull()
  })
})
