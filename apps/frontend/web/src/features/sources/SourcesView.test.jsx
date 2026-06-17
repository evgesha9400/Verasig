import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SourcesView } from './SourcesView.jsx'

const feeds = [
  { id: 'feed-1', status: 'analyzed' },
  { id: 'feed-2', status: 'backfilled' }
]

describe('SourcesView', () => {
  it('opens a connected source from a keyboard-accessible card button', async () => {
    const user = userEvent.setup()
    const onOpenTelegram = vi.fn()

    render(
      <SourcesView
        telegramConnected
        feeds={feeds}
        onConnectTelegram={() => {}}
        onOpenTelegram={onOpenTelegram}
      />
    )

    const sourceCard = screen.getByRole('button', { name: /telegram/i })
    sourceCard.focus()
    await user.keyboard('{Enter}')

    expect(onOpenTelegram).toHaveBeenCalledOnce()
  })
})
