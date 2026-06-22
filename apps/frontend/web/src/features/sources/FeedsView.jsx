/* Verasig prototype — Telegram feed list */
import { useState } from 'react'
import {
  Badge,
  Banner,
  Button,
  Dialog,
  IconButton,
  Input,
  Menu,
  MenuItem,
  MenuSeparator,
  Popover
} from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

const CONFIRM_COPY = {
  fetchNew: {
    title: 'Fetch new messages?',
    confirmLabel: 'Fetch new',
    variant: 'primary',
    icon: 'refresh',
    body: (feed) =>
      `Pull messages posted since the last backfill of ${feed.name}. Existing labels and rules are kept.`
  },
  refetchFull: {
    title: 'Re-fetch full history?',
    confirmLabel: 'Re-fetch all',
    variant: 'primary',
    icon: 'download',
    body: (feed) =>
      `Re-pull the entire history of ${feed.name} from the start. This can take a while; existing labels and rules are kept.`
  },
  remove: {
    title: 'Remove this feed?',
    confirmLabel: 'Remove feed',
    variant: 'danger',
    icon: 'alert',
    body: (feed) =>
      `${feed.name}, its labels, rules and score will be removed from your feeds. You can add it again later by its handle.`
  }
}

function fmtNum(n) {
  if (n == null) return '0'
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K'
  return String(n)
}

function deletedText(count) {
  return `${fmtNum(count)} deleted`
}

export function FeedsView({
  feeds,
  onStartBackfill,
  onRetry,
  onResume,
  onFetchNew,
  onRefetchFull,
  onReviewLabels,
  onRemove,
  onViewDeleted,
  onCheckGaps,
  checkingGapFeedId,
  onBacktest,
  onAddFeed
}) {
  const [tag, setTag] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState(null)
  const [confirm, setConfirm] = useState(null)

  function runConfirm() {
    if (!confirm) return
    const { kind, feed } = confirm
    setConfirm(null)
    if (kind === 'fetchNew') onFetchNew(feed)
    else if (kind === 'refetchFull') onRefetchFull(feed)
    else if (kind === 'remove') onRemove(feed)
  }

  async function addFeed(event) {
    event.preventDefault()
    if (!onAddFeed || !tag.trim()) return

    setAdding(true)
    setError(null)

    try {
      await onAddFeed(tag.trim())
      setTag('')
    } catch (caughtError) {
      setError(caughtError?.message || 'Could not add this Telegram feed.')
    } finally {
      setAdding(false)
    }
  }

  function FeedFlag({ kind, onLink }) {
    if (kind === 'gaps') {
      return (
        <Popover
          className="vrs-feed-pop"
          trigger={
            <Badge tone="pending" dot>
              History gaps
            </Badge>
          }
          onClick={(e) => e.stopPropagation()}
        >
          <span className="vrs-pilltip__t">
            <Icon name="alert" size={13} /> Possible history gaps
          </span>
          <span className="vrs-pilltip__b">
            The backfill found breaks in this feed&rsquo;s message ID sequence — some
            messages appear to be missing from the channel history. They may have been
            deleted. There&rsquo;s no confirmation that any of the deleted messages were
            signals.
          </span>
        </Popover>
      )
    }
    return (
      <Popover
        className="vrs-feed-pop"
        trigger={
          <Badge tone="rejected" dot>
            Scam
          </Badge>
        }
        onClick={(e) => e.stopPropagation()}
      >
        <span className="vrs-pilltip__t vrs-pilltip__t--danger">
          <Icon name="alert" size={13} /> Confirmed signal deletion
        </span>
        <span className="vrs-pilltip__b">
          A confirmed deleted message in this feed is labelled as a signal. Deleting
          losing or winning calls to rewrite a track record is a known scam pattern, so
          the quality score is floored to 0.
        </span>
        <Button
          variant="ghost"
          size="sm"
          iconLeft={<Icon name="externalLink" size={12} />}
          onClick={() => onLink && onLink()}
        >
          View deleted signals
        </Button>
      </Popover>
    )
  }

  function statusBadge(c) {
    if (c.status === 'verified')
      return (
        <Badge tone="verified" dot>
          Verified
        </Badge>
      )
    if (c.status === 'analyzed')
      return (
        <Badge tone="verified" dot>
          Analyzed
        </Badge>
      )
    if (c.status === 'cancelled')
      return (
        <Badge tone="pending" dot>
          Paused
        </Badge>
      )
    if (c.status === 'failed')
      return (
        <Badge tone="rejected" dot>
          Failed
        </Badge>
      )
    if (c.status === 'backfilled')
      return (
        <Badge tone="info" dot>
          Ready to label
        </Badge>
      )
    return null
  }

  function optionsMenu(c) {
    const busy = c.status === 'backfilling'
    const started = c.status !== 'new' && c.status !== 'backfilling'
    // Gaps only become meaningful once rules classify signals, i.e. after the
    // user has completed label + verify (status verified or analyzed).
    const reviewed = c.status === 'verified' || c.status === 'analyzed'
    const checkingGaps = checkingGapFeedId === c.id
    return (
      <Menu
        trigger={
          <IconButton label="Options">
            <Icon name="settings" size={16} />
          </IconButton>
        }
      >
        <MenuItem
          iconLeft={<Icon name="refresh" size={15} />}
          disabled={busy || !started}
          onClick={() => setConfirm({ kind: 'fetchNew', feed: c })}
        >
          Fetch new messages
        </MenuItem>
        <MenuItem
          iconLeft={<Icon name="download" size={15} />}
          disabled={busy || !started}
          onClick={() => setConfirm({ kind: 'refetchFull', feed: c })}
        >
          Re-fetch full history
        </MenuItem>
        <MenuItem
          iconLeft={<Icon name={checkingGaps ? 'refresh' : 'search'} size={15} />}
          disabled={busy || !reviewed || checkingGaps}
          aria-busy={checkingGaps}
          onClick={() => onCheckGaps && onCheckGaps(c)}
        >
          {checkingGaps ? 'Checking gaps' : 'Check gaps'}
        </MenuItem>
        {reviewed && (
          <MenuItem
            iconLeft={<Icon name="doc" size={15} />}
            disabled={busy}
            onClick={() => onReviewLabels && onReviewLabels(c)}
          >
            Review labels
          </MenuItem>
        )}
        <MenuSeparator />
        <MenuItem
          tone="danger"
          iconLeft={<Icon name="trash" size={15} />}
          disabled={busy}
          onClick={() => setConfirm({ kind: 'remove', feed: c })}
        >
          Remove feed
        </MenuItem>
      </Menu>
    )
  }

  function rightSide(c) {
    if (c.status === 'verified') {
      return (
        <div className="vrs-chat-right">
          <Button
            variant="primary"
            size="sm"
            iconLeft={<Icon name="chart" size={14} />}
            onClick={() => onBacktest && onBacktest(c)}
          >
            Backtest
          </Button>
          {optionsMenu(c)}
        </div>
      )
    }
    if (c.status === 'analyzed') {
      const scam = c.signalDeletion
      return (
        <div className="vrs-chat-right">
          <div className={`vrs-score ${scam ? 'vrs-score--zero' : ''}`}>
            <span className="vrs-score__v">{scam ? 0 : c.score}</span>
            <span className="vrs-score__l">Quality</span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            iconLeft={<Icon name="chart" size={14} />}
            onClick={() => onResume(c)}
          >
            Results
          </Button>
          {optionsMenu(c)}
        </div>
      )
    }
    if (c.status === 'cancelled' || c.status === 'failed') {
      return (
        <div className="vrs-chat-right">
          <div className="vrs-chat-progress">
            <span>{fmtNum(c.fetched)} fetched</span>
            <span>{c.lastDate ? `through ${c.lastDate}` : 'no date yet'}</span>
          </div>
          <Button
            variant="primary"
            size="sm"
            iconLeft={<Icon name="refresh" size={14} />}
            onClick={() => onRetry(c)}
          >
            Retry
          </Button>
          {optionsMenu(c)}
        </div>
      )
    }
    if (c.status === 'backfilled') {
      return (
        <div className="vrs-chat-right">
          <div className="vrs-chat-progress">{fmtNum(c.fetched)} messages</div>
          <Button
            variant="primary"
            size="sm"
            iconRight={<Icon name="arrowRight" size={14} />}
            onClick={() => onResume(c)}
          >
            Continue
          </Button>
          {optionsMenu(c)}
        </div>
      )
    }
    return (
      <div className="vrs-chat-right">
        <Button
          variant="secondary"
          size="sm"
          iconLeft={<Icon name="download" size={14} />}
          onClick={() => onStartBackfill(c)}
        >
          Start backfill
        </Button>
        {optionsMenu(c)}
      </div>
    )
  }

  return (
    <div className="vrs-page">
      <div className="vrs-sec-h">
        <span className="vrs-sec-t">Feeds from Telegram</span>
        <span className="vrs-sec-c">{feeds.length} available</span>
      </div>
      {onAddFeed && (
        <form className="vrs-form__actions" onSubmit={addFeed}>
          <Input
            label="Channel tag"
            mono
            value={tag}
            onChange={(event) => setTag(event.target.value)}
            placeholder="@pilot"
            disabled={adding}
          />
          <Button
            type="submit"
            variant="primary"
            loading={adding}
            disabled={!tag.trim()}
            iconLeft={<Icon name="plus" size={14} />}
          >
            Add feed
          </Button>
        </form>
      )}
      {error && (
        <Banner tone="rejected" title="Feed not added">
          {error}
        </Banner>
      )}
      <div className="vrs-stack-sm">
        {feeds.map((c) => (
          <div key={c.id} className="vrs-chat-row">
            <span className="vrs-chat-av" style={{ background: c.tint }}>
              {c.initials}
            </span>
            <div className="vrs-chat-main">
              <div className="vrs-chat-name">
                {c.name} {statusBadge(c)}
                {c.historyGaps &&
                  !c.signalDeletion &&
                  [
                    'backfilled',
                    'analyzed',
                    'cancelled',
                    'failed',
                    'verified'
                  ].includes(c.status) && <FeedFlag kind="gaps" />}
                {c.signalDeletion && ['verified', 'analyzed'].includes(c.status) && (
                  <FeedFlag
                    kind="scam"
                    onLink={() => onViewDeleted && onViewDeleted(c)}
                  />
                )}
              </div>
              <div className="vrs-chat-meta">
                <span>{c.tag}</span>
                <span className="dot" />
                <span>
                  <Icon
                    name="users"
                    size={12}
                    style={{ verticalAlign: '-2px', marginRight: 4 }}
                  />
                  {fmtNum(c.subscribers)} subscribers
                </span>
                {c.deletedCount > 0 && (
                  <>
                    <span className="dot" />
                    <span>{deletedText(c.deletedCount)}</span>
                  </>
                )}
                {c.status === 'analyzed' && !c.signalDeletion && (
                  <>
                    <span className="dot" />
                    <span style={{ color: 'var(--accent-text)' }}>
                      {c.winRate}% win · +{c.pnl}% PnL
                    </span>
                  </>
                )}
              </div>
            </div>
            {rightSide(c)}
          </div>
        ))}
      </div>
      {confirm && (
        <Dialog
          open
          onClose={() => setConfirm(null)}
          title={CONFIRM_COPY[confirm.kind].title}
          icon={<Icon name={CONFIRM_COPY[confirm.kind].icon} size={19} />}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setConfirm(null)}>
                Cancel
              </Button>
              <Button
                variant={CONFIRM_COPY[confirm.kind].variant}
                size="sm"
                onClick={runConfirm}
              >
                {CONFIRM_COPY[confirm.kind].confirmLabel}
              </Button>
            </>
          }
        >
          {CONFIRM_COPY[confirm.kind].body(confirm.feed)}
        </Dialog>
      )}
    </div>
  )
}
