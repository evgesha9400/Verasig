import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FeedsView } from './FeedsView.jsx'

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
  signalDeletion: true,
  deletedCount: 0
}

describe('FeedsView', () => {
  it('uses shared popover content for feed flags', () => {
    render(
      <FeedsView
        feeds={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
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
      <FeedsView
        feeds={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={onCheckGaps}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /check gaps/i }))

    expect(onCheckGaps).toHaveBeenCalledWith(feed)
  })

  it.each(['new', 'backfilling', 'backfilled', 'cancelled', 'failed'])(
    'disables Check gaps for %s feeds',
    (status) => {
      const unreviewedFeed = { ...feed, status, signalDeletion: false }

      render(
        <FeedsView
          feeds={[unreviewedFeed]}
          onStartBackfill={() => {}}
          onRetry={() => {}}
          onResume={() => {}}
          onFetchNew={() => {}}
          onRefetchFull={() => {}}
          onRemove={() => {}}
          onViewDeleted={() => {}}
          onCheckGaps={() => {}}
          onBacktest={() => {}}
        />
      )

      fireEvent.click(screen.getByRole('button', { name: 'Options' }))

      expect(screen.getByRole('menuitem', { name: /check gaps/i }).disabled).toBe(true)
    }
  )

  it.each(['verified', 'analyzed'])('enables Check gaps for %s feeds', (status) => {
    const reviewedFeed = { ...feed, status, signalDeletion: false }
    const onCheckGaps = vi.fn()

    render(
      <FeedsView
        feeds={[reviewedFeed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={onCheckGaps}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    const item = screen.getByRole('menuitem', { name: /check gaps/i })
    fireEvent.click(item)

    expect(item.disabled).toBe(false)
    expect(onCheckGaps).toHaveBeenCalledWith(reviewedFeed)
  })

  it('enables Check gaps for a backfilled feed with saved rules', () => {
    const reviewedFeed = {
      ...feed,
      status: 'backfilled',
      hasRisk: true,
      signalDeletion: false
    }
    const onCheckGaps = vi.fn()

    render(
      <FeedsView
        feeds={[reviewedFeed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={onCheckGaps}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    const item = screen.getByRole('menuitem', { name: /check gaps/i })
    fireEvent.click(item)

    expect(item.disabled).toBe(false)
    expect(onCheckGaps).toHaveBeenCalledWith(reviewedFeed)
  })

  it.each(['verified', 'analyzed'])('shows Review templates for %s feeds', (status) => {
    const reviewedFeed = { ...feed, status, signalDeletion: false }
    const onReviewTemplates = vi.fn()

    render(
      <FeedsView
        feeds={[reviewedFeed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onReviewTemplates={onReviewTemplates}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /review templates/i }))

    expect(onReviewTemplates).toHaveBeenCalledWith(reviewedFeed)
  })

  it('shows Backtest for a backfilled feed with saved rules', () => {
    const reviewedBackfilledFeed = {
      ...feed,
      status: 'backfilled',
      hasRisk: true,
      signalDeletion: false
    }
    const onBacktest = vi.fn()
    const onResume = vi.fn()

    render(
      <FeedsView
        feeds={[reviewedBackfilledFeed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={onResume}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onReviewTemplates={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={onBacktest}
      />
    )

    expect(screen.getByText('Ready to backtest')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /backtest/i }))

    expect(onBacktest).toHaveBeenCalledWith(reviewedBackfilledFeed)
    expect(onResume).not.toHaveBeenCalled()
  })

  it('keeps Fetch new messages wording in the menu and confirmation copy', async () => {
    render(
      <FeedsView
        feeds={[{ ...feed, status: 'verified', signalDeletion: false }]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /fetch new messages/i }))

    expect(await screen.findByText('Fetch new messages?')).toBeTruthy()
    expect(screen.getByText(/Existing labels and rules are kept/)).toBeTruthy()
  })

  it('shows a loading state while checking gaps', () => {
    const reviewedFeed = { ...feed, status: 'verified', signalDeletion: false }

    render(
      <FeedsView
        feeds={[reviewedFeed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        checkingGapFeedId={reviewedFeed.id}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    const item = screen.getByRole('menuitem', { name: /checking gaps/i })

    expect(item.disabled).toBe(true)
    expect(item.getAttribute('aria-busy')).toBe('true')
  })

  it('shows Scam badge on a verified feed with signal deletion', () => {
    render(
      <FeedsView
        feeds={[{ ...feed, status: 'verified', signalDeletion: true }]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    expect(screen.getByText('Scam')).toBeTruthy()
  })

  it('shows the cumulative deleted counter', () => {
    render(
      <FeedsView
        feeds={[{ ...feed, signalDeletion: false, deletedCount: 3 }]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    expect(screen.getByText('3 deleted')).toBeTruthy()
  })

  it('confirms before removing a feed', async () => {
    const onRemove = vi.fn()

    render(
      <FeedsView
        feeds={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={onRemove}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /remove feed/i }))

    expect(onRemove).not.toHaveBeenCalled()
    expect(await screen.findByText('Remove this feed?')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Remove feed' }))

    expect(onRemove).toHaveBeenCalledWith(feed)
  })

  it('confirms before fetching new messages', async () => {
    const onFetchNew = vi.fn()

    render(
      <FeedsView
        feeds={[feed]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={onFetchNew}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /fetch new messages/i }))

    fireEvent.click(screen.getByRole('button', { name: 'Fetch new' }))

    expect(onFetchNew).toHaveBeenCalledWith(feed)
  })

  it('adds a Telegram feed by channel tag', async () => {
    const onAddFeed = vi.fn().mockResolvedValue()

    render(
      <FeedsView
        feeds={[]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
        onAddFeed={onAddFeed}
      />
    )

    fireEvent.change(screen.getByLabelText(/channel tag/i), {
      target: { value: '@pilot' }
    })
    fireEvent.submit(screen.getByRole('button', { name: /add feed/i }).closest('form'))

    await waitFor(() => {
      expect(onAddFeed).toHaveBeenCalledWith('@pilot')
    })
  })

  it('shows the failure reason when adding a feed is rejected', async () => {
    const onAddFeed = vi
      .fn()
      .mockRejectedValue(new Error('Cannot resolve Telegram channel reference.'))

    render(
      <FeedsView
        feeds={[]}
        onStartBackfill={() => {}}
        onRetry={() => {}}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
        onAddFeed={onAddFeed}
      />
    )

    fireEvent.change(screen.getByLabelText(/channel tag/i), {
      target: { value: '@ghost' }
    })
    fireEvent.submit(screen.getByRole('button', { name: /add feed/i }).closest('form'))

    expect(await screen.findByText('Feed not added')).toBeTruthy()
    expect(screen.getByText('Cannot resolve Telegram channel reference.')).toBeTruthy()
  })

  it('shows failed backfill progress and retry action', () => {
    const failedFeed = {
      ...feed,
      status: 'failed',
      fetched: 200,
      lastDate: 'Jun 1, 2026',
      signalDeletion: false
    }
    const onRetry = vi.fn()

    render(
      <FeedsView
        feeds={[failedFeed]}
        onStartBackfill={() => {}}
        onRetry={onRetry}
        onResume={() => {}}
        onFetchNew={() => {}}
        onRefetchFull={() => {}}
        onRemove={() => {}}
        onViewDeleted={() => {}}
        onCheckGaps={() => {}}
        onBacktest={() => {}}
      />
    )

    expect(screen.getByText('Failed')).toBeTruthy()
    expect(screen.getByText('200 fetched')).toBeTruthy()
    expect(screen.getByText('through Jun 1, 2026')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))

    expect(onRetry).toHaveBeenCalledWith(failedFeed)
  })
})
