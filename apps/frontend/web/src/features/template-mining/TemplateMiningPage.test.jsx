import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateMiningPage } from './TemplateMiningPage.jsx'

const feed = { id: 'apex', name: 'Apex Crypto Calls' }

// Offline (no authToken): the auto-run falls back to the bundled demo history.
function renderPage(props = {}) {
  return render(<TemplateMiningPage activeFeed={feed} {...props} />)
}

function stagePill(label) {
  return screen.getByText(label).closest('.vrs-tm-stage')
}

describe('TemplateMiningPage', () => {
  it('auto-runs against the active feed with no manual button click', () => {
    renderPage()

    // Metrics and family cards appear on entry — no "Run" click required.
    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getByText('Families found')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
  })

  it('mines the stored messages from the connected feed when authenticated', async () => {
    const messages = [
      {
        id: 'f1',
        date: 'Jun 6',
        time: '08:42',
        author: 'Apex',
        text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355'
      },
      { id: 'f2', date: 'Jun 6', time: '09:00', author: 'Apex', text: 'gm team' }
    ]
    const onListMessages = vi.fn().mockResolvedValue({ messages })
    render(
      <TemplateMiningPage
        activeFeed={feed}
        authToken="jwt"
        onListMessages={onListMessages}
      />
    )

    expect(onListMessages).toHaveBeenCalledWith('apex')
    expect(await screen.findByText('Messages scanned')).toBeTruthy()
    expect(await screen.findAllByText('<INSTRUMENT>')).toBeTruthy()
  })

  it('re-mines when the active feed changes', async () => {
    const messages = [{ id: 'f1', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340' }]
    const first = vi.fn().mockResolvedValue({ messages })
    const { rerender } = render(
      <TemplateMiningPage activeFeed={feed} authToken="jwt" onListMessages={first} />
    )
    expect(first).toHaveBeenCalledWith('apex')
    expect(await screen.findByText('Messages scanned')).toBeTruthy()

    const next = vi.fn().mockResolvedValue({ messages })
    rerender(
      <TemplateMiningPage
        activeFeed={{ id: 'delta', name: 'Delta' }}
        authToken="jwt"
        onListMessages={next}
      />
    )
    expect(next).toHaveBeenCalledWith('delta')
    expect(await screen.findByText('Messages scanned')).toBeTruthy()
  })

  it('moves the indicator Mine → Review → Confirm as decisions are made', async () => {
    const user = userEvent.setup()
    renderPage()

    // A result exists but nothing is accepted yet: Review is active.
    expect(stagePill('Review').classList.contains('is-active')).toBe(true)
    expect(stagePill('Confirm').classList.contains('is-active')).toBe(false)

    await user.click(screen.getByRole('button', { name: /Apply suggestions/i }))

    // At least one family accepted: Confirm is active.
    expect(stagePill('Confirm').classList.contains('is-active')).toBe(true)
    expect(stagePill('Review').classList.contains('is-active')).toBe(false)
  })

  it('compiles rules and populates the audit when families are accepted', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /Apply suggestions/i }))

    // A deterministic parser rule is compiled and shown verbatim.
    expect(screen.getAllByText(/"confidenceThreshold"/).length).toBeGreaterThan(0)
    // The audit ran over the full history — the review surface shows its tabs.
    expect(screen.getByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Rejected/i })).toBeTruthy()
  })

  it('never renders NaN in the audit queues', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /Apply suggestions/i }))

    expect(screen.queryByText(/NaN/)).toBeNull()
  })

  it('lets a single decision accept a whole family', async () => {
    const user = userEvent.setup()
    renderPage()

    const acceptButtons = screen.getAllByRole('button', {
      name: /Accept as signal format/i
    })
    await user.click(acceptButtons[0])

    expect(screen.getAllByText('Accepted').length).toBeGreaterThan(0)
  })

  it('still supports the sample dataset through the alternate-source disclosure', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Sample dataset'))
    await user.click(screen.getByRole('button', { name: /Run template mining/i }))

    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
  })

  it('wires the audit gate to onFinish and onKeepVerified', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()
    const onKeepVerified = vi.fn()
    renderPage({ onFinish, onKeepVerified })

    await user.click(screen.getByRole('button', { name: /Apply suggestions/i }))

    const review = screen.getByText('Review results').closest('.vrs-tm-review')
    await user.click(
      within(review).getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(onFinish).toHaveBeenCalledTimes(1)

    await user.click(within(review).getByRole('button', { name: /Keep verified/i }))
    expect(onKeepVerified).toHaveBeenCalledTimes(1)
  })

  it('threads a provided overlay into mining', async () => {
    const user = userEvent.setup()
    const messages = [{ id: 'o1', text: 'АПТ 🚀\nEntry: 2.5\nStop: 2.4\nTarget: 2.7' }]
    const onListMessages = vi.fn().mockResolvedValue({ messages })
    render(
      <TemplateMiningPage
        activeFeed={feed}
        authToken="jwt"
        onListMessages={onListMessages}
        overlay={{
          instrumentAliases: { АПТ: 'APTUSDT' },
          directionTokens: { '🚀': 'BUY' }
        }}
      />
    )
    expect(await screen.findByText('Messages scanned')).toBeTruthy()
    // The extraction table (where APTUSDT would render) is behind the card's
    // expand toggle; open it before checking the overlay reached the detectors.
    await user.click(await screen.findByRole('button', { name: /Show all/i }))
    expect(await screen.findAllByText(/APTUSDT/)).toBeTruthy()
  })
})
