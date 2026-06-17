/* Verasig prototype — Sources page */
import { Badge, Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { SourceCard } from '../../shared/components/SourceCard.jsx'

const telegramLogo = (
  <span
    className="vrs-src-logo"
    style={{
      background: 'color-mix(in srgb, #2AABEE 22%, transparent)',
      color: '#3CB4F0'
    }}
  >
    <Icon name="telegram" fill />
  </span>
)

export function SourcesView({
  telegramConnected,
  feeds,
  onConnectTelegram,
  onOpenTelegram
}) {
  const analyzed = feeds.filter((c) => c.status === 'analyzed').length
  const inProgress = feeds.filter((c) =>
    ['backfilling', 'cancelled', 'failed', 'backfilled', 'labeling'].includes(c.status)
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
            <SourceCard
              onClick={onOpenTelegram}
              logo={telegramLogo}
              name="Telegram"
              kind="Signal source · MTProto"
              badge={
                <Badge tone="verified" dot>
                  Connected
                </Badge>
              }
              desc={
                <>
                  {feeds.length} feeds available · {analyzed} analyzed
                  {inProgress ? ` · ${inProgress} in progress` : ''}.
                </>
              }
              meta={
                <>
                  <Icon name="users" size={13} /> mara@northwave.io
                </>
              }
              action={
                <span className="vrs-src-card__cta">
                  Open
                  <Icon name="arrowRight" size={14} />
                </span>
              }
            />
          ) : (
            <SourceCard
              empty
              desc={
                <>
                  No sources connected yet.
                  <br />
                  Connect Telegram below to begin.
                </>
              }
            />
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
            <SourceCard
              logo={telegramLogo}
              name="Telegram"
              kind="Signal source · MTProto"
              desc="Ingest messages from any channel or group you belong to. Backfill full history and verify signal quality."
              meta={
                <>
                  <Icon name="clock" size={13} /> ~2 min setup
                </>
              }
              action={
                <Button
                  variant="primary"
                  size="sm"
                  iconLeft={<Icon name="plus" size={14} />}
                  onClick={onConnectTelegram}
                >
                  Connect
                </Button>
              }
            />
          )}
        </div>
      </div>
    </div>
  )
}
