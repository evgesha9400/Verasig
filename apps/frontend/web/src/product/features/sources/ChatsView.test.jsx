import { fireEvent, render, screen } from '@testing-library/react'
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
})
