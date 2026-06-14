import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChatsView } from './ChatsView.jsx'

const feed = {
  id: 'delta',
  name: 'Delta Futures',
  initials: 'DF',
  tint: '#5197ff',
  source: 'telegram',
  status: 'analyzed',
  score: 86,
  fetched: 18420,
  lastDate: 'Jun 6',
  signalDeletion: true
}

describe('ChatsView', () => {
  it('uses shared popover content for feed flags', () => {
    render(
      <ChatsView
        chats={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onReanalyze={() => {}}
        onRestart={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    expect(screen.getByRole('tooltip').textContent).toContain(
      'Confirmed signal deletion'
    )
  })

  it('uses shared menu item roles for feed options', () => {
    const onCheckGaps = vi.fn()

    render(
      <ChatsView
        chats={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onReanalyze={() => {}}
        onRestart={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={onCheckGaps}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /check gaps/i }))

    expect(onCheckGaps).toHaveBeenCalledWith(feed)
  })

  it('adds a Telegram feed by channel tag', async () => {
    const onAddChat = vi.fn().mockResolvedValue()

    render(
      <ChatsView
        chats={[]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onReanalyze={() => {}}
        onRestart={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
        onAddChat={onAddChat}
      />
    )

    fireEvent.change(screen.getByLabelText(/channel tag/i), {
      target: { value: '@pilot' }
    })
    fireEvent.submit(screen.getByRole('button', { name: /add feed/i }).closest('form'))

    await waitFor(() => {
      expect(onAddChat).toHaveBeenCalledWith('@pilot')
    })
  })

  it('shows the failure reason when adding a feed is rejected', async () => {
    const onAddChat = vi
      .fn()
      .mockRejectedValue(new Error('Cannot resolve Telegram channel reference.'))

    render(
      <ChatsView
        chats={[]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onReanalyze={() => {}}
        onRestart={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
        onAddChat={onAddChat}
      />
    )

    fireEvent.change(screen.getByLabelText(/channel tag/i), {
      target: { value: '@ghost' }
    })
    fireEvent.submit(screen.getByRole('button', { name: /add feed/i }).closest('form'))

    expect(await screen.findByText('Feed not added')).toBeTruthy()
    expect(screen.getByText('Cannot resolve Telegram channel reference.')).toBeTruthy()
  })
})
