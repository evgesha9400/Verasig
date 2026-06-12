/* Verasig prototype — Sources page */
import { Badge, Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

export function SourcesView({
  telegramConnected,
  chats,
  onConnectTelegram,
  onOpenTelegram
}) {
  const analyzed = chats.filter((c) => c.status === 'analyzed').length
  const inProgress = chats.filter((c) =>
    ['backfilling', 'cancelled', 'backfilled', 'labeling'].includes(c.status)
  ).length

  return (
    <div className="vrs-page">
      {/* Connected */}
      <div>
        <div className="vrs-sec-h">
          <span className="vrs-sec-t">Connected sources</span>
        </div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {telegramConnected ? (
            <div className="vrs-src-card is-clickable" onClick={onOpenTelegram}>
              <div className="vrs-src-card__top">
                <span
                  className="vrs-src-logo"
                  style={{
                    background: 'color-mix(in srgb, #2AABEE 22%, transparent)',
                    color: '#3CB4F0'
                  }}
                >
                  <Icon name="telegram" fill />
                </span>
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">Telegram</div>
                  <div className="vrs-src-card__kind">Signal source · MTProto</div>
                </div>
                <Badge tone="verified" dot>
                  Connected
                </Badge>
              </div>
              <div className="vrs-src-card__desc">
                {chats.length} feeds available · {analyzed} analyzed
                {inProgress ? ` · ${inProgress} in progress` : ''}.
              </div>
              <div className="vrs-src-card__foot">
                <span className="vrs-src-meta">
                  <Icon name="users" size={13} /> mara@northwave.io
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  iconRight={<Icon name="arrowRight" size={14} />}
                >
                  Open
                </Button>
              </div>
            </div>
          ) : (
            <div
              className="vrs-src-card"
              style={{
                borderStyle: 'dashed',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                minHeight: 168,
                color: 'var(--text-faint)'
              }}
            >
              <div className="vrs-src-card__desc" style={{ flex: 'none' }}>
                No sources connected yet.
                <br />
                Connect Telegram below to begin.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Available */}
      <div>
        <div className="vrs-sec-h">
          <span className="vrs-sec-t">Available to configure</span>
        </div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {!telegramConnected && (
            <div className="vrs-src-card">
              <div className="vrs-src-card__top">
                <span
                  className="vrs-src-logo"
                  style={{
                    background: 'color-mix(in srgb, #2AABEE 22%, transparent)',
                    color: '#3CB4F0'
                  }}
                >
                  <Icon name="telegram" fill />
                </span>
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">Telegram</div>
                  <div className="vrs-src-card__kind">Signal source · MTProto</div>
                </div>
              </div>
              <div className="vrs-src-card__desc">
                Ingest messages from any channel or group you belong to. Backfill full
                history and verify signal quality.
              </div>
              <div className="vrs-src-card__foot">
                <span className="vrs-src-meta">
                  <Icon name="clock" size={13} /> ~2 min setup
                </span>
                <Button
                  variant="primary"
                  size="sm"
                  iconLeft={<Icon name="plus" size={14} />}
                  onClick={onConnectTelegram}
                >
                  Connect
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
