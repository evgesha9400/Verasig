import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateExamplesDialog } from './TemplateExamplesDialog.jsx'

/* Every message in a template, paged 5 at a time, in a modal — so a reviewer can
   double-check the whole grouping and decide without leaving the review. */

function makeCandidate(index, confidence = 0.9) {
  return {
    message: { id: `m${index}`, text: `MSG-${index} body` },
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
    rejectionReasons: []
  }
}

function groupOf(candidates, geometryWarnings = 0) {
  return {
    id: 'tpl_x',
    templateKey: 'tpl_x',
    normalizedTemplate: 'BUY <INSTRUMENT>',
    candidates,
    examples: [...candidates].sort((a, b) => b.confidence - a.confidence).slice(0, 5),
    count: candidates.length,
    dateRange: { from: 'Jun 1', to: 'Jun 2' },
    confidenceAvg: 0.85,
    intentDistribution: { new_signal: candidates.length },
    geometryWarnings
  }
}

function makeGroup(messageCount) {
  return groupOf(Array.from({ length: messageCount }, (_, i) => makeCandidate(i + 1)))
}

function renderDialog(group, props = {}) {
  return render(
    <TemplateExamplesDialog
      group={group}
      open
      onClose={vi.fn()}
      status="unreviewed"
      onAccept={vi.fn()}
      onReject={vi.fn()}
      onReset={vi.fn()}
      {...props}
    />
  )
}

describe('TemplateExamplesDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <TemplateExamplesDialog group={makeGroup(3)} open={false} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows five messages per page with the window and total', () => {
    renderDialog(makeGroup(7))
    expect(screen.getByText('MSG-1 body')).toBeTruthy()
    expect(screen.getByText('MSG-5 body')).toBeTruthy()
    expect(screen.queryByText('MSG-6 body')).toBeNull()
    expect(screen.getByText(/1\s*[–-]\s*5 of 7/)).toBeTruthy()
  })

  it('pages forward to reveal the remaining messages', async () => {
    const user = userEvent.setup()
    renderDialog(makeGroup(7))
    await user.click(screen.getByRole('button', { name: /Next/i }))
    expect(screen.queryByText('MSG-1 body')).toBeNull()
    expect(screen.getByText('MSG-7 body')).toBeTruthy()
    expect(screen.getByText(/6\s*[–-]\s*7 of 7/)).toBeTruthy()
  })

  it('orders the list by confidence', () => {
    renderDialog(
      groupOf([makeCandidate(1, 0.5), makeCandidate(2, 0.95), makeCandidate(3, 0.7)])
    )
    const order = screen.getAllByText(/MSG-\d body/).map((el) => el.textContent)
    expect(order).toEqual(['MSG-2 body', 'MSG-3 body', 'MSG-1 body'])
  })

  it('surfaces the geometry warning and the extraction table', () => {
    const { container } = renderDialog(groupOf([makeCandidate(1)], 2))
    expect(container.querySelector('.vrs-tm-legend')).toBeTruthy()
    expect(screen.getByText(/suspicious stop\/target geometry/i)).toBeTruthy()
    expect(screen.getAllByText('Instrument').length).toBeGreaterThan(0)
  })

  it('lets the reviewer decide from the footer', async () => {
    const user = userEvent.setup()
    const onAccept = vi.fn()
    renderDialog(makeGroup(3), { onAccept })
    await user.click(screen.getByRole('button', { name: /^Accept$/i }))
    expect(onAccept).toHaveBeenCalledTimes(1)
  })
})
