import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'

/* The expanded message list pages through EVERY message in a family (5 per page),
   not just the top examples — so a reviewer can double-check the whole grouping. */

function makeCandidate(index, confidence = 0.9) {
  return {
    message: { id: `m${index}`, text: `MSG-${index} body`, date: 'Jun 1' },
    instruments: [],
    directions: [],
    prices: [],
    fields: {
      instrument: 'BTCUSDT',
      direction: 'BUY',
      orderType: 'market',
      entry: null,
      stopLoss: null,
      takeProfits: []
    },
    intent: 'new_signal',
    confidence,
    rejectionReasons: [],
    templateKey: 'tpl_x',
    normalizedTemplate: 'BUY <INSTRUMENT>'
  }
}

function groupFromCandidates(candidates) {
  return {
    id: 'tpl_x',
    templateKey: 'tpl_x',
    normalizedTemplate: 'BUY <INSTRUMENT>',
    candidates,
    examples: [...candidates].sort((a, b) => b.confidence - a.confidence).slice(0, 5),
    count: candidates.length,
    dateRange: { from: 'Jun 1', to: 'Jun 2' },
    confidenceAvg: 0.85,
    intentDistribution: {
      new_signal: candidates.length,
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

function makeGroup(messageCount) {
  const candidates = Array.from({ length: messageCount }, (_, i) =>
    makeCandidate(i + 1)
  )
  return {
    id: 'tpl_x',
    templateKey: 'tpl_x',
    normalizedTemplate: 'BUY <INSTRUMENT>',
    candidates,
    examples: candidates.slice(0, 5),
    count: messageCount,
    dateRange: { from: 'Jun 1', to: 'Jun 2' },
    confidenceAvg: 0.85,
    intentDistribution: {
      new_signal: messageCount,
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

function renderCard(group, { expanded = false } = {}) {
  return render(
    <TemplateGroupCard
      group={group}
      status="unreviewed"
      expanded={expanded}
      onAccept={vi.fn()}
      onReject={vi.fn()}
      onReset={vi.fn()}
      onToggleExamples={vi.fn()}
    />
  )
}

describe('TemplateGroupCard message list', () => {
  it('offers to show ALL messages by total count, not a fixed example sample', () => {
    renderCard(makeGroup(7))
    expect(screen.getByRole('button', { name: /Show all 7 messages/i })).toBeTruthy()
  })

  it('shows five messages per page when expanded', () => {
    renderCard(makeGroup(7), { expanded: true })

    // Page 1: first five messages present, the rest hidden.
    expect(screen.getByText('MSG-1 body')).toBeTruthy()
    expect(screen.getByText('MSG-5 body')).toBeTruthy()
    expect(screen.queryByText('MSG-6 body')).toBeNull()
    expect(screen.queryByText('MSG-7 body')).toBeNull()
    // The total is visible alongside the current window.
    expect(screen.getByText(/1\s*[–-]\s*5 of 7/)).toBeTruthy()
  })

  it('pages forward to reveal the remaining messages', async () => {
    const user = userEvent.setup()
    renderCard(makeGroup(7), { expanded: true })

    await user.click(screen.getByRole('button', { name: /Next/i }))

    expect(screen.queryByText('MSG-1 body')).toBeNull()
    expect(screen.getByText('MSG-6 body')).toBeTruthy()
    expect(screen.getByText('MSG-7 body')).toBeTruthy()
    expect(screen.getByText(/6\s*[–-]\s*7 of 7/)).toBeTruthy()
  })

  it('does not paginate a family that fits on one page', () => {
    renderCard(makeGroup(3), { expanded: true })
    expect(screen.getByText('MSG-3 body')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Next/i })).toBeNull()
  })

  it('orders the list by confidence so the leading row matches the representative', () => {
    // Insertion order (1,2,3) differs from confidence order (2,3,1).
    const group = groupFromCandidates([
      makeCandidate(1, 0.5),
      makeCandidate(2, 0.95),
      makeCandidate(3, 0.7)
    ])
    renderCard(group, { expanded: true })

    const order = screen.getAllByText(/MSG-\d body/).map((el) => el.textContent)
    expect(order).toEqual(['MSG-2 body', 'MSG-3 body', 'MSG-1 body'])
  })

  it('marks a boundary control aria-disabled but keeps it focusable (no focus loss)', () => {
    renderCard(makeGroup(7), { expanded: true })
    const prev = screen.getByRole('button', { name: /Prev/i })
    const next = screen.getByRole('button', { name: /Next/i })

    // On page one, Prev is the bound; it is aria-disabled, NOT natively disabled.
    expect(prev.getAttribute('aria-disabled')).toBe('true')
    expect(prev.hasAttribute('disabled')).toBe(false)
    expect(next.getAttribute('aria-disabled')).toBe('false')
  })

  it('announces the page window as a live status region', () => {
    renderCard(makeGroup(7), { expanded: true })
    const status = screen.getByRole('status')
    expect(status.getAttribute('aria-live')).toBe('polite')
    expect(status.textContent).toMatch(/1\s*[–-]\s*5 of 7/)
  })
})
