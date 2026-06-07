import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Play,
  RotateCcw,
  Search,
  Send,
  X,
} from "lucide-react"
import type { ReactNode } from "react"
import { readerHash } from "./routing"
import {
  isResumable,
  progressOf,
  type ChatSummary,
  type SourceChat,
} from "./sourceChats"

type ChatsPageProps = {
  visibleChats: SourceChat[]
  totalChats: number
  summary: ChatSummary
  loading: boolean
  runningChat: SourceChat | undefined
  secondsRemaining: number
  searchQuery: string
  onSearchChange: (value: string) => void
  onStartBackfill: (chatId: string) => void
  onCancelBackfill: (chatId: string) => void
}

function ChatsPage({
  visibleChats,
  totalChats,
  summary,
  loading,
  runningChat,
  secondsRemaining,
  searchQuery,
  onSearchChange,
  onStartBackfill,
  onCancelBackfill,
}: ChatsPageProps) {
  const backfillActive = runningChat !== undefined

  return (
    <section className="chats-frame" aria-label="Telegram chats">
      <SourceConnectionBar summary={summary} />
      <ChatsControls searchQuery={searchQuery} onSearchChange={onSearchChange} />
      {runningChat && (
        <ActiveBackfillBar
          chat={runningChat}
          secondsRemaining={secondsRemaining}
          onCancel={onCancelBackfill}
        />
      )}
      <ChatList
        backfillActive={backfillActive}
        loading={loading}
        searchQuery={searchQuery}
        totalChats={totalChats}
        visibleChats={visibleChats}
        onStartBackfill={onStartBackfill}
        onCancelBackfill={onCancelBackfill}
      />
    </section>
  )
}

function SourceConnectionBar({ summary }: { summary: ChatSummary }) {
  return (
    <header className="connection-bar" aria-label="Connected source">
      <div className="connection-identity">
        <span className="connection-mark" aria-hidden="true">
          <Send size={18} strokeWidth={2.2} />
        </span>
        <div className="connection-text">
          <h1 className="connection-title">Telegram chats</h1>
          <p className="connection-status">
            <span className="status-dot" aria-hidden="true" />
            Connected
          </p>
        </div>
      </div>
      <dl className="connection-stats">
        <ConnectionStat label="Chats" value={String(summary.total)} />
        <ConnectionStat label="Backfilled" value={String(summary.backfilled)} />
        <ConnectionStat label="Pending" value={String(summary.pending)} />
        <ConnectionStat
          label="Captured"
          value={formatExactCount(summary.capturedTotal)}
        />
      </dl>
    </header>
  )
}

function ConnectionStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="connection-stat">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function ChatsControls({
  searchQuery,
  onSearchChange,
}: {
  searchQuery: string
  onSearchChange: (value: string) => void
}) {
  return (
    <section className="chats-controls" aria-label="Chat controls">
      <label className="search-field" aria-label="Search chats">
        <Search size={16} aria-hidden="true" />
        <input
          aria-label="Search chats"
          placeholder="Search chats by name or handle..."
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
    </section>
  )
}

function ActiveBackfillBar({
  chat,
  secondsRemaining,
  onCancel,
}: {
  chat: SourceChat
  secondsRemaining: number
  onCancel: (chatId: string) => void
}) {
  const progress = progressOf(chat)

  return (
    <aside className="active-backfill" aria-label="Active backfill">
      <div className="active-backfill-head">
        <span className="active-label">
          <span className="status-dot status-dot-running" aria-hidden="true" />
          Backfilling
        </span>
        <strong className="active-title">{chat.title}</strong>
        <span className="active-pct">{progress.percent}%</span>
      </div>
      <ProgressTrack percent={progress.percent} label={`Backfilling ${chat.title}`} />
      <div className="active-backfill-foot">
        <span className="active-count">
          {formatExactCount(progress.captured)} / ~
          {formatExactCount(progress.estimated)} messages
        </span>
        <span className="active-sep" aria-hidden="true">
          ·
        </span>
        <span className="active-eta">{formatEta(secondsRemaining)}</span>
        <button
          className="ghost-button"
          type="button"
          onClick={() => onCancel(chat.id)}
        >
          <X size={15} aria-hidden="true" />
          Cancel
        </button>
      </div>
    </aside>
  )
}

function ChatList({
  backfillActive,
  loading,
  searchQuery,
  totalChats,
  visibleChats,
  onStartBackfill,
  onCancelBackfill,
}: {
  backfillActive: boolean
  loading: boolean
  searchQuery: string
  totalChats: number
  visibleChats: SourceChat[]
  onStartBackfill: (chatId: string) => void
  onCancelBackfill: (chatId: string) => void
}) {
  if (loading) {
    return <ChatListSkeleton />
  }

  if (visibleChats.length === 0) {
    return <ChatsEmpty searchQuery={searchQuery} totalChats={totalChats} />
  }

  return (
    <ul className="chat-list" aria-label="Available chats">
      {visibleChats.map((chat) => (
        <ChatRow
          backfillActive={backfillActive}
          chat={chat}
          key={chat.id}
          onCancelBackfill={onCancelBackfill}
          onStartBackfill={onStartBackfill}
        />
      ))}
    </ul>
  )
}

function ChatRow({
  backfillActive,
  chat,
  onCancelBackfill,
  onStartBackfill,
}: {
  backfillActive: boolean
  chat: SourceChat
  onCancelBackfill: (chatId: string) => void
  onStartBackfill: (chatId: string) => void
}) {
  return (
    <li className={`chat-row chat-row-${chat.status}`}>
      <div className="chat-main">
        <div className="chat-headline">
          <h2 className="chat-title">{chat.title}</h2>
          <ChatHandle chat={chat} />
        </div>
        <p className="chat-meta">
          <span className="chat-subs">
            {formatCompactCount(chat.subscriberCount)} subscribers
          </span>
          <span
            className="proxy-tag"
            title="Subscriber count is a popularity proxy, not a quality signal"
          >
            proxy
          </span>
          <span className="chat-sep" aria-hidden="true">
            ·
          </span>
          <span className="chat-capture">{captureLabel(chat)}</span>
        </p>
      </div>
      <div className="chat-aside">
        <ChatActions
          backfillActive={backfillActive}
          chat={chat}
          onCancelBackfill={onCancelBackfill}
          onStartBackfill={onStartBackfill}
        />
      </div>
    </li>
  )
}

function ChatHandle({ chat }: { chat: SourceChat }) {
  if (chat.handle) {
    return <span className="chat-handle">{chat.handle}</span>
  }

  return <span className="chat-private">Private channel</span>
}

function ChatActions({
  backfillActive,
  chat,
  onCancelBackfill,
  onStartBackfill,
}: {
  backfillActive: boolean
  chat: SourceChat
  onCancelBackfill: (chatId: string) => void
  onStartBackfill: (chatId: string) => void
}) {
  if (chat.status === "complete") {
    return (
      <>
        <span className="status-pill status-pill-complete">
          <CheckCircle2 size={14} aria-hidden="true" />
          Complete
        </span>
        <a className="open-reader" href={readerHash(chat.id)}>
          Open reader
          <ArrowRight size={15} aria-hidden="true" />
        </a>
      </>
    )
  }

  if (chat.status === "running") {
    const progress = progressOf(chat)
    return (
      <>
        <div className="row-progress">
          <ProgressTrack
            percent={progress.percent}
            label={`Backfilling ${chat.title}`}
          />
          <span className="row-progress-pct">{progress.percent}%</span>
        </div>
        <button
          className="ghost-button"
          type="button"
          onClick={() => onCancelBackfill(chat.id)}
        >
          <X size={15} aria-hidden="true" />
          Cancel
        </button>
      </>
    )
  }

  if (chat.status === "failed") {
    return (
      <>
        <span className="status-pill status-pill-failed">
          <AlertTriangle size={14} aria-hidden="true" />
          Failed
        </span>
        <StartButton
          backfillActive={backfillActive}
          chatId={chat.id}
          icon={<RotateCcw size={15} aria-hidden="true" />}
          label="Retry"
          onStartBackfill={onStartBackfill}
        />
      </>
    )
  }

  if (isResumable(chat)) {
    return (
      <>
        <span className="status-pill status-pill-paused">Paused</span>
        <StartButton
          backfillActive={backfillActive}
          chatId={chat.id}
          icon={<Play size={15} aria-hidden="true" />}
          label="Resume backfill"
          onStartBackfill={onStartBackfill}
        />
      </>
    )
  }

  return (
    <StartButton
      backfillActive={backfillActive}
      chatId={chat.id}
      icon={<Play size={15} aria-hidden="true" />}
      label="Start backfill"
      onStartBackfill={onStartBackfill}
    />
  )
}

function StartButton({
  backfillActive,
  chatId,
  icon,
  label,
  onStartBackfill,
}: {
  backfillActive: boolean
  chatId: string
  icon: ReactNode
  label: string
  onStartBackfill: (chatId: string) => void
}) {
  return (
    <button
      className="start-backfill"
      type="button"
      disabled={backfillActive}
      title={
        backfillActive
          ? "Finish or cancel the active backfill first"
          : undefined
      }
      onClick={() => onStartBackfill(chatId)}
    >
      {icon}
      {label}
    </button>
  )
}

function ProgressTrack({ percent, label }: { percent: number; label: string }) {
  return (
    <div
      className="progress-track"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
    >
      <div className="progress-fill" style={{ width: `${percent}%` }} />
    </div>
  )
}

function ChatListSkeleton() {
  return (
    <div className="chat-list" role="status" aria-label="Loading chats">
      {Array.from({ length: 6 }, (_, index) => (
        <div className="chat-row chat-row-skeleton" key={index} aria-hidden="true">
          <div className="chat-main">
            <span className="skeleton skeleton-title" />
            <span className="skeleton skeleton-meta" />
          </div>
          <span className="skeleton skeleton-action" />
        </div>
      ))}
    </div>
  )
}

function ChatsEmpty({
  searchQuery,
  totalChats,
}: {
  searchQuery: string
  totalChats: number
}) {
  if (totalChats === 0) {
    return (
      <div className="chats-empty" role="status">
        <p className="chats-empty-title">No Telegram chats found</p>
        <p className="chats-empty-hint">
          Join channels from the connected Telegram account, then reload.
        </p>
      </div>
    )
  }

  return (
    <div className="chats-empty" role="status">
      <p className="chats-empty-title">No chats match "{searchQuery.trim()}"</p>
      <p className="chats-empty-hint">Clear the search to see all chats.</p>
    </div>
  )
}

const compactFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})

const exactFormatter = new Intl.NumberFormat("en-US")

function formatCompactCount(value: number): string {
  return compactFormatter.format(value)
}

function formatExactCount(value: number): string {
  return exactFormatter.format(value)
}

function formatEta(seconds: number): string {
  if (seconds <= 0) {
    return "finishing up"
  }

  if (seconds < 60) {
    return `~${seconds}s left`
  }

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  if (remainder === 0) {
    return `~${minutes}m left`
  }

  return `~${minutes}m ${remainder}s left`
}

function captureLabel(chat: SourceChat): string {
  const progress = progressOf(chat)

  if (chat.status === "complete") {
    return `${formatExactCount(progress.captured)} messages captured`
  }

  if (chat.status === "running") {
    return `${formatExactCount(progress.captured)} / ~${formatExactCount(
      progress.estimated,
    )} captured`
  }

  if (chat.status === "failed") {
    return chat.failureReason ?? "Backfill failed"
  }

  if (isResumable(chat)) {
    return `${formatExactCount(progress.captured)} of ~${formatExactCount(
      progress.estimated,
    )} captured · paused`
  }

  return `Not yet backfilled · ~${formatExactCount(progress.estimated)} messages`
}

export default ChatsPage
