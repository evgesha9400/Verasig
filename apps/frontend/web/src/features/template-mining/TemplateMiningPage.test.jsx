import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateMiningPage } from './TemplateMiningPage.jsx'

const feed = { id: 'apex', name: 'Apex Crypto Calls' }

// Offline (no authToken): the auto-run falls back to the bundled demo history and
// advances Mine → Review synchronously as the effects settle.
function renderPage(props = {}) {
  return render(<TemplateMiningPage activeFeed={feed} {...props} />)
}

function step(label) {
  return screen.getByText(label).closest('.vrs-tm-step')
}

function acceptFirstTemplate(user) {
  const acceptButtons = screen.getAllByRole('button', {
    name: /Accept as signal format/i
  })
  return user.click(acceptButtons[0])
}

describe('TemplateMiningPage', () => {
  it('auto-runs and lands on Review with no manual button click', () => {
    renderPage()
    expect(step('Review').classList.contains('is-active')).toBe(true)
    expect(step('Mine').classList.contains('is-done')).toBe(true)
    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
  })

  it('mines the connected feed history when authenticated', async () => {
    const messages = [
      { id: 'f1', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355' },
      { id: 'f2', text: 'gm team' }
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
  })

  it('re-mines when the active feed changes', async () => {
    const messages = [{ id: 'f1', text: 'XAUUSD BUY NOW\nSL 2312\nTP 2340' }]
    const first = vi.fn().mockResolvedValue({ messages })
    const { rerender } = render(
      <TemplateMiningPage activeFeed={feed} authToken="jwt" onListMessages={first} />
    )
    expect(first).toHaveBeenCalledWith('apex')
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

  it('renders the Suggested accept and Needs review sections', () => {
    renderPage()
    expect(screen.getByText('Suggested accept')).toBeTruthy()
    expect(screen.getByText('Needs review')).toBeTruthy()
  })

  it('gates "Continue to verify" until a template is accepted', async () => {
    const user = userEvent.setup()
    renderPage()
    const continueBtn = screen.getByRole('button', { name: /Continue to verify/i })
    expect(continueBtn.disabled).toBe(true)
    expect(screen.getByText(/Accept at least one template to continue/i)).toBeTruthy()

    await acceptFirstTemplate(user)
    expect(screen.getByRole('button', { name: /Continue to verify/i }).disabled).toBe(
      false
    )
  })

  it('shows the audit only after continuing to Verify, and can go back', async () => {
    const user = userEvent.setup()
    renderPage()
    // Review does not show the audit tabs yet.
    expect(screen.queryByRole('tab', { name: /Parsed/i })).toBeNull()

    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    expect(screen.getByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(step('Verify').classList.contains('is-active')).toBe(true)

    await user.click(screen.getByRole('button', { name: /Back to review/i }))
    expect(step('Review').classList.contains('is-active')).toBe(true)
  })

  it('Apply all accepts the suggested templates', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /Apply all/i }))
    expect(screen.getAllByText('Accepted').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Continue to verify/i }).disabled).toBe(
      false
    )
  })

  it('does not render the compiled-rules JSON panel', async () => {
    const user = userEvent.setup()
    renderPage()
    await acceptFirstTemplate(user)
    expect(screen.queryByText(/"confidenceThreshold"/)).toBeNull()
  })

  it('keeps the overlay manager under the Advanced disclosure', () => {
    renderPage({ onSaveOverlay: vi.fn() })
    const advanced = screen.getByText('Advanced').closest('details')
    expect(within(advanced).getByText('Coin aliases')).toBeTruthy()
  })

  it('wires the audit gate to onFinish and onKeepVerified', async () => {
    const user = userEvent.setup()
    const onFinish = vi.fn()
    const onKeepVerified = vi.fn()
    renderPage({ onFinish, onKeepVerified })
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))

    const review = screen.getByText('Review results').closest('.vrs-tm-review')
    await user.click(
      within(review).getByRole('button', { name: /Confirm & route to Exchange/i })
    )
    expect(onFinish).toHaveBeenCalledTimes(1)
    await user.click(within(review).getByRole('button', { name: /Keep verified/i }))
    expect(onKeepVerified).toHaveBeenCalledTimes(1)
  })

  it('still supports the sample dataset through the alternate-source disclosure', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByText('Sample dataset'))
    await user.click(screen.getByRole('button', { name: /Run template mining/i }))
    expect(screen.getByText('Messages scanned')).toBeTruthy()
  })

  it('never renders NaN', async () => {
    const user = userEvent.setup()
    renderPage()
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    expect(screen.queryByText(/NaN/)).toBeNull()
  })
})
