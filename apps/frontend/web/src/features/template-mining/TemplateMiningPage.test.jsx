import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateMiningPage } from './TemplateMiningPage.jsx'
import {
  FEED_MESSAGES,
  mineTemplateGroups
} from '../../domain/template-mining/index.js'

const feed = { id: 'apex', name: 'Apex Crypto Calls' }

// Mirrors how ProductApp drives the page: the parent owns the current step and
// advances it in response to the page's callbacks. Offline (no authToken) the
// auto-run falls back to the bundled demo history and lands on Review.
function Harness({ activeFeed = feed, startStep = 'mine', ...props }) {
  const [step, setStep] = useState(startStep)
  return (
    <TemplateMiningPage
      activeFeed={activeFeed}
      step={step}
      onMined={() => setStep('review')}
      onContinueToVerify={() => setStep('verify')}
      onBackToReview={() => setStep('review')}
      {...props}
    />
  )
}

function renderPage(props = {}) {
  return render(<Harness {...props} />)
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
    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
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

    await user.click(screen.getByRole('button', { name: /Back to review/i }))
    expect(screen.getByRole('button', { name: /Continue to verify/i })).toBeTruthy()
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

  it('no longer offers the alternate-source disclosure', () => {
    renderPage()
    expect(screen.queryByText(/Use sample or pasted messages instead/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /Run template mining/i })).toBeNull()
  })

  it('never renders NaN', async () => {
    const user = userEvent.setup()
    renderPage()
    await acceptFirstTemplate(user)
    await user.click(screen.getByRole('button', { name: /Continue to verify/i }))
    expect(screen.queryByText(/NaN/)).toBeNull()
  })

  it('closes the examples modal after Accept', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Accept$/ }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('closes the examples modal after Reject', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Reject$/ }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('keeps the examples modal open after Reset', async () => {
    const user = userEvent.setup()
    renderPage()
    // Decide on the card first so the modal opens already-accepted (shows Reset).
    await user.click(
      screen.getAllByRole('button', { name: /Accept as signal format/i })[0]
    )
    await user.click(
      screen.getAllByRole('button', { name: /View all .* messages/i })[0]
    )
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^Reset$/ }))
    expect(screen.queryByRole('dialog')).toBeTruthy()
  })
})

// Reopening a verified feed lands on Verify with empty decisions. The page must
// re-mine, then reseed the accepted templates recovered from the backend so the
// audit repopulates — instead of bouncing back to Review as if nothing was done.
function mountVerifyResume({ acceptedTemplateKeys }) {
  const onStartMine = vi.fn().mockResolvedValue({ jobId: 'user:7:mine' })
  const stream = {}
  const onStreamMine = vi.fn((_id, handlers) => {
    stream.handlers = handlers
    return { close: vi.fn() }
  })
  const onLoadConfirmed = vi.fn().mockResolvedValue({ acceptedTemplateKeys })
  const onBackToReview = vi.fn()
  render(
    <TemplateMiningPage
      activeFeed={{ id: '7', name: 'Pilot Signals' }}
      authToken="jwt-token"
      step="verify"
      onStartMine={onStartMine}
      onStreamMine={onStreamMine}
      onLoadConfirmed={onLoadConfirmed}
      onBackToReview={onBackToReview}
    />
  )
  return { stream, onLoadConfirmed, onBackToReview }
}

// A failed server mine must keep the operator on an explicit error with a retry
// affordance, not just flash a toast and leave a blank loader behind.
function mountAuthedMine() {
  const onStartMine = vi.fn().mockResolvedValue({ jobId: 'user:7:mine' })
  const stream = {}
  const onStreamMine = vi.fn((_id, handlers) => {
    stream.handlers = handlers
    return { close: vi.fn() }
  })
  const fireToast = vi.fn()
  render(
    <TemplateMiningPage
      activeFeed={{ id: '7', name: 'Pilot Signals', tag: '@pilot' }}
      authToken="jwt-token"
      step="mine"
      onStartMine={onStartMine}
      onStreamMine={onStreamMine}
      fireToast={fireToast}
      onMined={vi.fn()}
    />
  )
  return { stream, onStartMine, fireToast }
}

describe('TemplateMiningPage — mine failure', () => {
  it('shows an error with a retry affordance and re-runs on retry', async () => {
    const user = userEvent.setup()
    const { stream, onStartMine, fireToast } = mountAuthedMine()

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

describe('TemplateMiningPage — resume a verified feed', () => {
  it('reseeds the confirmed templates and shows the audit (no bounce)', async () => {
    const groups = mineTemplateGroups(FEED_MESSAGES)
    const confirmedKey = groups[0].templateKey
    const { stream, onLoadConfirmed, onBackToReview } = mountVerifyResume({
      acceptedTemplateKeys: [confirmedKey]
    })

    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone({ groups, messages: FEED_MESSAGES }))

    expect(await screen.findByRole('tab', { name: /Parsed/i })).toBeTruthy()
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
    expect(onBackToReview).not.toHaveBeenCalled()
  })

  it('falls back to Review when no confirmed templates come back', async () => {
    const groups = mineTemplateGroups(FEED_MESSAGES)
    const { stream, onLoadConfirmed, onBackToReview } = mountVerifyResume({
      acceptedTemplateKeys: []
    })

    await waitFor(() => expect(stream.handlers).toBeTruthy())
    act(() => stream.handlers.onDone({ groups, messages: FEED_MESSAGES }))

    await waitFor(() => expect(onBackToReview).toHaveBeenCalled())
    expect(onLoadConfirmed).toHaveBeenCalledWith('7')
  })
})
