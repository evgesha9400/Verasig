import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TemplateMiningPage } from './TemplateMiningPage.jsx'

function renderPage() {
  return render(<TemplateMiningPage feeds={[]} />)
}

async function runOnSample(user) {
  await user.click(screen.getByText('Sample dataset'))
  await user.click(screen.getByRole('button', { name: /Run template mining/i }))
}

describe('TemplateMiningPage', () => {
  it('starts with an intro prompt and no results', () => {
    renderPage()
    expect(screen.getByText(/Pick a source and run the miner/i)).toBeTruthy()
    expect(screen.queryByText('Template families')).toBeNull()
  })

  it('mines the sample dataset and shows metrics and family cards', async () => {
    const user = userEvent.setup()
    renderPage()
    await runOnSample(user)

    expect(screen.getByText('Messages scanned')).toBeTruthy()
    expect(screen.getByText('Families found')).toBeTruthy()
    expect(screen.getAllByText('<INSTRUMENT>').length).toBeGreaterThan(0)
  })

  it('compiles rules and populates the audit when families are accepted', async () => {
    const user = userEvent.setup()
    renderPage()
    await runOnSample(user)
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
    await runOnSample(user)
    await user.click(screen.getByRole('button', { name: /Apply suggestions/i }))

    // Rejected rows carry no confidence; they must not surface "NaN%".
    expect(screen.queryByText(/NaN/)).toBeNull()
  })

  it('mines the stored messages from the connected feed when authenticated', async () => {
    const user = userEvent.setup()
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
        feeds={[{ id: 'apex', name: 'Apex Crypto Calls' }]}
        authToken="jwt"
        onListMessages={onListMessages}
      />
    )

    await user.click(screen.getByRole('button', { name: /Run template mining/i }))

    expect(onListMessages).toHaveBeenCalledWith('apex')
    expect(await screen.findByText('Messages scanned')).toBeTruthy()
    expect(await screen.findAllByText('<INSTRUMENT>')).toBeTruthy()
  })

  it('lets a single decision accept a whole family', async () => {
    const user = userEvent.setup()
    renderPage()
    await runOnSample(user)

    const acceptButtons = screen.getAllByRole('button', {
      name: /Accept as signal format/i
    })
    await user.click(acceptButtons[0])

    expect(screen.getAllByText('Accepted').length).toBeGreaterThan(0)
  })

  it('threads a provided overlay into mining', async () => {
    const user = userEvent.setup()
    const messages = [{ id: 'o1', text: 'АПТ 🚀\nEntry: 2.5\nStop: 2.4\nTarget: 2.7' }]
    const onListMessages = vi.fn().mockResolvedValue({ messages })
    render(
      <TemplateMiningPage
        feeds={[{ id: 'apex', name: 'Apex' }]}
        authToken="jwt"
        onListMessages={onListMessages}
        overlay={{
          instrumentAliases: { 'АПТ': 'APTUSDT' },
          directionTokens: { '🚀': 'BUY' }
        }}
      />
    )
    await user.click(screen.getByRole('button', { name: /Run template mining/i }))
    expect(await screen.findByText('Messages scanned')).toBeTruthy()
    // APTUSDT only appears if the overlay reached the detectors.
    expect(await screen.findAllByText(/APTUSDT/)).toBeTruthy()
  })
})
