import { describe, expect, it } from 'vitest'
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
    // The audit ran over the full history.
    expect(screen.getByText('Parsed signals')).toBeTruthy()
    expect(screen.getByText('Rejected updates / results')).toBeTruthy()
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
})
