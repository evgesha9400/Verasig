/* Verasig prototype — Telegram chat list */
import { useState } from 'react';
import { Badge, Button, IconButton } from '@verasig/design-system';
import { Icon } from '@verasig/design-system';

function fmtNum(n) {
  if (n >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'K';
  return String(n);
}

export function ChatsView({ chats, onStartBackfill, onRetry, onResume, onReanalyze, onRestart, onViewDeleted, onCheckGaps, onBacktest }) {
  const [menuFor, setMenuFor] = useState(null);

  function FeedFlag({ kind, onLink }) {
    if (kind === 'gaps') {
      return (
        <span className="vrs-pilltip" onClick={(e) => e.stopPropagation()}>
          <Badge tone="pending" dot>History gaps</Badge>
          <span className="vrs-pilltip__pop" role="tooltip">
            <span className="vrs-pilltip__t"><Icon name="alert" size={13} /> Possible history gaps</span>
            <span className="vrs-pilltip__b">The backfill found breaks in this feed&rsquo;s message ID sequence — some messages appear to be missing from the channel history. They may have been deleted. There&rsquo;s no confirmation that any of the deleted messages were signals.</span>
          </span>
        </span>
      );
    }
    return (
      <span className="vrs-pilltip vrs-pilltip--danger" onClick={(e) => e.stopPropagation()}>
        <Badge tone="rejected" dot>Scam</Badge>
        <span className="vrs-pilltip__pop" role="tooltip">
          <span className="vrs-pilltip__t vrs-pilltip__t--danger"><Icon name="alert" size={13} /> Confirmed signal deletion</span>
          <span className="vrs-pilltip__b">On the latest backfill, messages previously classified as signals are gone from this feed&rsquo;s history. Deleting losing &mdash; or winning &mdash; calls to rewrite a track record is a known scam pattern, so the quality score is floored to 0.</span>
          <button className="vrs-pilltip__link" onClick={(e) => { e.stopPropagation(); onLink && onLink(); }}>
            <Icon name="externalLink" size={12} /> View deleted signals
          </button>
        </span>
      </span>
    );
  }

  function statusBadge(c) {
    if (c.status === 'verified') return <Badge tone="verified" dot>Verified</Badge>;
    if (c.status === 'analyzed') return <Badge tone="verified" dot>Analyzed</Badge>;
    if (c.status === 'cancelled') return <Badge tone="pending" dot>Paused</Badge>;
    if (c.status === 'backfilled') return <Badge tone="info" dot>Ready to label</Badge>;
    return null;
  }

  function optionsMenu(c) {
    return (
      <div style={{ position: 'relative' }}>
        <IconButton label="Options" onClick={(e) => { e.stopPropagation(); setMenuFor(menuFor === c.id ? null : c.id); }}>
          <Icon name="settings" size={16} />
        </IconButton>
        {menuFor === c.id && (
          <div className="vrs-menu" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => { setMenuFor(null); onReanalyze(c); }}><Icon name="refresh" size={15} /> Backfill new signals</button>
            <button onClick={() => { setMenuFor(null); onCheckGaps && onCheckGaps(c); }}><Icon name="search" size={15} /> Check gaps</button>
            <button className="danger" onClick={() => { setMenuFor(null); onRestart(c); }}><Icon name="trash" size={15} /> Delete & restart</button>
          </div>
        )}
      </div>
    );
  }

  function rightSide(c) {
    if (c.status === 'verified') {
      return (
        <div className="vrs-chat-right">
          <Button variant="primary" size="sm" iconLeft={<Icon name="chart" size={14} />} onClick={(e) => { e.stopPropagation(); onBacktest && onBacktest(c); }}>Backtest</Button>
          {optionsMenu(c)}
        </div>
      );
    }
    if (c.status === 'analyzed') {
      const scam = c.signalDeletion;
      return (
        <div className="vrs-chat-right">
          <div className={`vrs-score ${scam ? 'vrs-score--zero' : ''}`}>
            <span className="vrs-score__v">{scam ? 0 : c.score}</span>
            <span className="vrs-score__l">Quality</span>
          </div>
          {optionsMenu(c)}
        </div>
      );
    }
    if (c.status === 'cancelled') {
      return (
        <div className="vrs-chat-right">
          <div className="vrs-chat-progress">{fmtNum(c.fetched)} fetched<br/>through {c.lastDate}</div>
          <Button variant="primary" size="sm" iconLeft={<Icon name="refresh" size={14} />} onClick={(e) => { e.stopPropagation(); onRetry(c); }}>Retry</Button>
        </div>
      );
    }
    if (c.status === 'backfilled') {
      return (
        <div className="vrs-chat-right">
          <div className="vrs-chat-progress">{fmtNum(c.fetched)} messages</div>
          <Button variant="primary" size="sm" iconRight={<Icon name="arrowRight" size={14} />} onClick={(e) => { e.stopPropagation(); onResume(c); }}>Continue</Button>
        </div>
      );
    }
    return (
      <div className="vrs-chat-right">
        <Button variant="secondary" size="sm" iconLeft={<Icon name="download" size={14} />} onClick={(e) => { e.stopPropagation(); onStartBackfill(c); }}>Start backfill</Button>
      </div>
    );
  }

  const clickable = (c) => c.status === 'analyzed' || c.status === 'backfilled' || c.status === 'verified';

  return (
    <div className="vrs-page" onClick={() => setMenuFor(null)}>
      <div className="vrs-sec-h">
        <span className="vrs-sec-t">Feeds from Telegram</span>
        <span className="vrs-sec-c">{chats.length} available</span>
      </div>
      <div className="vrs-stack-sm">
        {chats.map((c) => (
          <div key={c.id} className={`vrs-chat-row ${clickable(c) ? 'is-clickable' : ''}`}
            onClick={clickable(c) ? () => (c.status === 'verified' ? (onBacktest && onBacktest(c)) : onResume(c)) : undefined}>
            <span className="vrs-chat-av" style={{ background: c.tint }}>{c.initials}</span>
            <div className="vrs-chat-main">
              <div className="vrs-chat-name">{c.name} {statusBadge(c)}{c.historyGaps && !c.signalDeletion && ['backfilled', 'analyzed', 'cancelled', 'verified'].includes(c.status) && <FeedFlag kind="gaps" />}{c.signalDeletion && c.status === 'analyzed' && <FeedFlag kind="scam" onLink={() => onViewDeleted && onViewDeleted(c)} />}</div>
              <div className="vrs-chat-meta">
                <span>{c.tag}</span>
                <span className="dot" />
                <span><Icon name="users" size={12} style={{ verticalAlign: '-2px', marginRight: 4 }} />{fmtNum(c.subscribers)} subscribers</span>
                {c.status === 'analyzed' && !c.signalDeletion && (<><span className="dot" /><span style={{ color: 'var(--accent-text)' }}>{c.winRate}% win · +{c.pnl}% PnL</span></>)}
              </div>
            </div>
            {rightSide(c)}
          </div>
        ))}
      </div>
    </div>
  );
}
