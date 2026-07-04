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
  Popover,
  Select
} from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

const DEPTH_OPTIONS = [
  { value: '6m', label: '6 months' },
  { value: '1y', label: '1 year' },
  { value: 'all', label: 'All history' }
]

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
    title: 'Wipe & re-fetch full history?',
    confirmLabel: 'Wipe & re-fetch',
    variant: 'danger',
    icon: 'alert',
    body: (feed) =>
      `This removes the captured history of ${feed.name} and recaptures it from Telegram. The message counter restarts at zero. Template decisions, saved rules and deletion evidence are kept.`
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

function deletedText(feed) {
  const base = `${fmtNum(feed.deletedCount)} deleted`
  const signals = feed.deletedSignalCount || 0
  if (signals === 0) return base
  return `${base} · ${signals} signal${signals === 1 ? '' : 's'}`
}

function isReviewedFeed(feed) {
  return feed.status === 'verified' || feed.status === 'analyzed' || feed.hasRisk
}

export function FeedsView({
  feeds,
  onOpenFeed,
  onFetchNew,
  onRefetchFull,
  onReviewTemplates,
  onRemove,
  onViewDeleted,
  onCheckGaps,
  checkingGapFeedId,
  rescanScanned,
  onAddFeed
}) {
  const [tag, setTag] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [refetchDepth, setRefetchDepth] = useState('1y')

  function runConfirm() {
    if (!confirm) return
    const { kind, feed } = confirm
    setConfirm(null)
    if (kind === 'fetchNew') onFetchNew(feed)
    else if (kind === 'refetchFull') onRefetchFull(feed, refetchDepth)
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

  function ScamFlag({ onLink }) {
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
          {c.hasRisk ? 'Ready to backtest' : 'Ready to label'}
        </Badge>
      )
    return null
  }

  function optionsMenu(c) {
    const busy = c.status === 'backfilling'
    const started = c.status !== 'new' && c.status !== 'backfilling'
    // Gaps only become meaningful once rules classify signals.
    const reviewed = isReviewedFeed(c)
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
            onClick={() => onReviewTemplates && onReviewTemplates(c)}
          >
            Review templates
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

  // The row itself navigates (onOpenFeed); the right side shows status info and
  // the gear only. The gear stops propagation so it never triggers row nav.
  function rightSide(c) {
    return (
      <div className="vrs-feed-right">
        {c.status === 'analyzed' && (
          <div className={`vrs-score ${c.signalDeletion ? 'vrs-score--zero' : ''}`}>
            <span className="vrs-score__v">{c.signalDeletion ? 0 : c.score}</span>
            <span className="vrs-score__l">Quality</span>
          </div>
        )}
        {(c.status === 'cancelled' || c.status === 'failed') && (
          <div className="vrs-feed-progress">
            <span>{fmtNum(c.fetched)} fetched</span>
            <span>{c.lastDate ? `through ${c.lastDate}` : 'no date yet'}</span>
          </div>
        )}
        {c.status === 'backfilled' && (
          <div className="vrs-feed-progress">{fmtNum(c.fetched)} messages</div>
        )}
        <span onClick={(e) => e.stopPropagation()}>{optionsMenu(c)}</span>
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
          <div
            key={c.id}
            className="vrs-feed-row"
            role="button"
            tabIndex={0}
            style={{ cursor: 'pointer' }}
            onClick={() => onOpenFeed && onOpenFeed(c)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onOpenFeed && onOpenFeed(c)
              }
            }}
          >
            <span className="vrs-feed-av" style={{ background: c.tint }}>
              {c.initials}
            </span>
            <div className="vrs-feed-main">
              <div className="vrs-feed-name">
                {c.name} {statusBadge(c)}
                {c.signalDeletion && ['verified', 'analyzed'].includes(c.status) && (
                  <ScamFlag onLink={() => onViewDeleted && onViewDeleted(c)} />
                )}
              </div>
              <div className="vrs-feed-meta">
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
                {checkingGapFeedId === c.id && rescanScanned != null && (
                  <>
                    <span className="dot" />
                    <span>checking · {fmtNum(rescanScanned)} scanned</span>
                  </>
                )}
                {c.deletedCount > 0 && (
                  <>
                    <span className="dot" />
                    <span>{deletedText(c)}</span>
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
          {confirm.kind === 'refetchFull' && (
            <div style={{ marginTop: 'var(--space-3)' }}>
              <Select
                label="History depth"
                options={DEPTH_OPTIONS}
                value={refetchDepth}
                onChange={(event) => setRefetchDepth(event.target.value)}
              />
            </div>
          )}
        </Dialog>
      )}
    </div>
  )
}
