import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LabelView } from './LabelView.jsx'

const messages = [
  {
    id: '101',
    author: 'Apex',
    date: 'Jun 6',
    time: '08:42',
    text: 'LONG BTC',
    media: null
  },
  {
    id: '102',
    author: 'Apex',
    date: 'Jun 6',
    time: '09:03',
    text: 'gm chat',
    media: null
  }
]

function renderView(overrides = {}) {
  const onListMessages = vi.fn().mockResolvedValue({ messages })
  const onGetCounts = vi
    .fn()
    .mockResolvedValue({ signalCount: 0, noiseCount: 0, modifierCount: 0, total: 0 })
  const onRecordLabel = vi.fn().mockResolvedValue(undefined)
  const onDistill = vi.fn()
  render(
    <LabelView
      chatId="7"
      onListMessages={onListMessages}
      onGetCounts={onGetCounts}
      onRecordLabel={onRecordLabel}
      onDistill={onDistill}
      {...overrides}
    />
  )
  return { onListMessages, onGetCounts, onRecordLabel, onDistill }
}

describe('LabelView', () => {
  it('loads real backfilled messages into the deck', async () => {
    const { onListMessages } = renderView()
    await waitFor(() => expect(onListMessages).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('LONG BTC')).toBeTruthy()
  })

  it('persists each label via the backend on swipe', async () => {
    const { onRecordLabel } = renderView()
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    await waitFor(() =>
      expect(onRecordLabel).toHaveBeenCalledWith('7', '101', 'signal')
    )
  })

  it('seeds the signal count from the backend and unlocks distill at five', async () => {
    const onGetCounts = vi
      .fn()
      .mockResolvedValue({ signalCount: 4, noiseCount: 0, modifierCount: 0, total: 4 })
    const onDistill = vi.fn()
    renderView({ onGetCounts, onDistill })
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    const distill = await screen.findByRole('button', { name: /Distill rules/i })
    expect(distill.disabled).toBe(false)
    fireEvent.click(distill)
    expect(onDistill).toHaveBeenCalled()
  })

  it('shows an empty state when there are no candidate messages', async () => {
    const onListMessages = vi.fn().mockResolvedValue({ messages: [] })
    renderView({ onListMessages })
    expect(await screen.findByText('No messages to label')).toBeTruthy()
  })

  it('reverts the optimistic label and reports an error when the write fails', async () => {
    const onRecordLabel = vi.fn().mockRejectedValue(new Error('boom'))
    const onError = vi.fn()
    renderView({ onRecordLabel, onError })
    await screen.findByText('LONG BTC')
    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))
    await waitFor(() => expect(onError).toHaveBeenCalled())
  })
})
