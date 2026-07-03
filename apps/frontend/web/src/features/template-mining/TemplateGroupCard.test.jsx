import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateGroupCard } from './TemplateGroupCard.jsx'

/* The card is the compact unit of review: template + stats + decide/inspect
   controls. Inspecting every message happens in a modal, not by stretching the
   card in place. */

function makeGroup(messageCount) {
  const candidates = Array.from({ length: messageCount }, (_, i) => ({
    message: { id: `m${i + 1}`, text: `MSG-${i + 1} body` },
    fields: { instrument: 'BTCUSDT', direction: 'BUY', orderType: 'market' },
    intent: 'new_signal',
    confidence: 0.9,
    rejectionReasons: []
  }))
  return {
    id: 'tpl_x',
    templateKey: 'tpl_x',
    normalizedTemplate: 'BUY <INSTRUMENT>',
    candidates,
    examples: candidates.slice(0, 5),
    count: messageCount,
    dateRange: { from: 'Jun 1', to: 'Jun 2' },
    confidenceAvg: 0.85,
    intentDistribution: { new_signal: messageCount },
    geometryWarnings: 0,
    status: 'unreviewed',
    suggestedAction: 'accept'
  }
}

function renderCard(props = {}) {
  return render(
    <TemplateGroupCard
      group={makeGroup(7)}
      status="unreviewed"
      onAccept={vi.fn()}
      onReject={vi.fn()}
      onReset={vi.fn()}
      onShowExamples={vi.fn()}
      {...props}
    />
  )
}

describe('TemplateGroupCard', () => {
  it('offers to view all messages by total count', () => {
    renderCard()
    expect(screen.getByRole('button', { name: /View all 7 messages/i })).toBeTruthy()
  })

  it('opens the examples modal instead of expanding in place', async () => {
    const user = userEvent.setup()
    const onShowExamples = vi.fn()
    renderCard({ onShowExamples })
    await user.click(screen.getByRole('button', { name: /View all 7 messages/i }))
    expect(onShowExamples).toHaveBeenCalledTimes(1)
    // No in-card message list or extraction table on the card itself.
    expect(screen.queryByText('MSG-1 body')).toBeNull()
    expect(screen.queryByText('Instrument')).toBeNull()
  })

  it('fires accept and reject decisions', async () => {
    const user = userEvent.setup()
    const onAccept = vi.fn()
    const onReject = vi.fn()
    renderCard({ onAccept, onReject })
    await user.click(screen.getByRole('button', { name: /Accept as signal format/i }))
    await user.click(screen.getByRole('button', { name: /Reject as noise/i }))
    expect(onAccept).toHaveBeenCalledTimes(1)
    expect(onReject).toHaveBeenCalledTimes(1)
  })

  it('shows the decided status and a Reset control once decided', () => {
    renderCard({ status: 'accepted' })
    expect(screen.getAllByText('Accepted').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Reset/i })).toBeTruthy()
  })
})
