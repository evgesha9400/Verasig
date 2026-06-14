/* Verasig prototype — Telegram chat list */
import { useState } from 'react'
import {
  Badge,
  Banner,
  Button,
  IconButton,
  Input,
  Menu,
  MenuItem,
  Popover
} from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

function fmtNum(n) {
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K'
  return String(n)
}

export function ChatsView({
  chats,
  onStartBackfill,
  onRetry,
  onResume,
  onReanalyze,
  onRestart,
  onViewDeleted,
  onCheckGaps,
  onBacktest,
  onAddChat
}) {
  const [tag, setTag] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState(null)

  async function addChat(event) {
    event.preventDefault()
    if (!onAddChat || !tag.trim()) return

    setAdding(true)
    setError(null)

    try {
      await onAddChat(tag.trim())
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
          On the latest backfill, messages previously classified as signals are gone
          from this feed&rsquo;s history. Deleting losing &mdash; or winning &mdash;
          calls to rewrite a track record is a known scam pattern, so the quality score
          is floored to 0.
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
    if (c.status === 'backfilled')
      return (
        <Badge tone="info" dot>
          Ready to label
        </Badge>
      )
    return null
  }

  function optionsMenu(c) {
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
          onClick={() => onReanalyze(c)}
        >
          Backfill new signals
        </MenuItem>
        <MenuItem
          iconLeft={<Icon name="search" size={15} />}
          onClick={() => onCheckGaps && onCheckGaps(c)}
        >
          Check gaps
        </MenuItem>
        <MenuItem
          tone="danger"
          iconLeft={<Icon name="trash" size={15} />}
          onClick={() => onRestart(c)}
        >
          Delete & restart
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
    if (c.status === 'cancelled') {
      return (
        <div className="vrs-chat-right">
          <div className="vrs-chat-progress">
            {fmtNum(c.fetched)} fetched
            <br />
            through {c.lastDate}
          </div>
          <Button
            variant="primary"
            size="sm"
            iconLeft={<Icon name="refresh" size={14} />}
            onClick={() => onRetry(c)}
          >
            Retry
          </Button>
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
      </div>
    )
  }

  return (
    <div className="vrs-page">
      <div className="vrs-sec-h">
        <span className="vrs-sec-t">Feeds from Telegram</span>
        <span className="vrs-sec-c">{chats.length} available</span>
      </div>
      {onAddChat && (
        <form className="vrs-form__actions" onSubmit={addChat}>
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
        {chats.map((c) => (
          <div key={c.id} className="vrs-chat-row">
            <span className="vrs-chat-av" style={{ background: c.tint }}>
              {c.initials}
            </span>
            <div className="vrs-chat-main">
              <div className="vrs-chat-name">
                {c.name} {statusBadge(c)}
                {c.historyGaps &&
                  !c.signalDeletion &&
                  ['backfilled', 'analyzed', 'cancelled', 'verified'].includes(
                    c.status
                  ) && <FeedFlag kind="gaps" />}
                {c.signalDeletion && c.status === 'analyzed' && (
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
    </div>
  )
}
