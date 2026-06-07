import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Image as ImageIcon,
  MessageSquare,
  Search,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react"
import { useMemo, useState } from "react"
import "./App.css"
import {
  DEFAULT_PAGE_SIZE,
  filterMessages,
  labelMessage,
  paginateMessages,
  sortMessagesNewestFirst,
  summarizeLabels,
  type LabelValue,
  type MessageFilter,
  type SourceFeed,
  type SourceMessage,
} from "./sourceLabeling"

const selectedFeed: SourceFeed = {
  id: "crypto-alpha-signals",
  sourceType: "telegram",
  name: "Crypto Alpha Signals",
  handle: "@cryptoalphasignals",
  capturedCount: 152_842,
  backfillStatus: "complete",
}

const initialMessages = makeSourceMessages()

function App() {
  const [messages, setMessages] = useState(initialMessages)
  const [filter, setFilter] = useState<MessageFilter>("unlabeled")
  const [searchQuery, setSearchQuery] = useState("")
  const [page, setPage] = useState(1)

  const sortedMessages = useMemo(
    () => sortMessagesNewestFirst(messages),
    [messages],
  )
  const visibleMessages = useMemo(
    () => filterMessages(sortedMessages, filter, searchQuery),
    [filter, searchQuery, sortedMessages],
  )
  const pageSlice = paginateMessages(visibleMessages, page, DEFAULT_PAGE_SIZE)
  const stats = summarizeLabels(messages)

  function saveMessageLabel(messageId: string, label: LabelValue) {
    setMessages((currentMessages) => labelMessage(currentMessages, messageId, label))
  }

  function selectMessageFilter(value: MessageFilter) {
    setFilter(value)
    setPage(1)
  }

  return (
    <main className="app-shell">
      <header className="app-bar">
        <a className="brand" href="/" aria-label="Verasig home">
          <span className="brand-mark" aria-hidden="true">
            <CheckCircle2 size={18} strokeWidth={2.4} />
          </span>
          <span>Verasig</span>
        </a>
        <nav className="app-nav" aria-label="Primary">
          <a aria-current="page" href="#sources">
            Sources
          </a>
          <a href="#distillation">Distillation</a>
        </nav>
        <div className="account-chip" aria-label="Signed in account">
          EV
        </div>
      </header>

      <section className="reader-frame" aria-label="Source labeling reader">
        <SourceToolbar feed={selectedFeed} />
        <StatsStrip stats={stats} />
        <ReaderControls
          filter={filter}
          onFilterChange={selectMessageFilter}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />
        <MessageTable
          messages={pageSlice.items}
          onLabelMessage={saveMessageLabel}
        />
        <Pagination
          end={pageSlice.end}
          page={pageSlice.page}
          pageCount={pageSlice.pageCount}
          pageSize={pageSlice.pageSize}
          start={pageSlice.start}
          total={pageSlice.total}
          onNext={() => setPage((currentPage) => currentPage + 1)}
          onPrevious={() => setPage((currentPage) => currentPage - 1)}
        />
      </section>
    </main>
  )
}

function SourceToolbar({ feed }: { feed: SourceFeed }) {
  return (
    <section className="source-toolbar" aria-label="Selected source">
      <label className="field field-compact">
        <span>Source type</span>
        <select aria-label="Source type" value={feed.sourceType} disabled>
          <option value="telegram">Telegram</option>
        </select>
      </label>

      <label className="field field-feed">
        <span>Feed</span>
        <select aria-label="Feed" value={feed.id} disabled>
          <option value={feed.id}>{feed.name}</option>
        </select>
        <small>{feed.handle}</small>
      </label>

      <div className="status-block" aria-label="Backfill status">
        <span>Status</span>
        <strong>
          <CheckCircle2 size={16} aria-hidden="true" />
          Backfill complete
        </strong>
        <small>{formatNumber(feed.capturedCount)} messages</small>
      </div>

      <label className="field field-compact">
        <span>Page size</span>
        <select aria-label="Page size" value={DEFAULT_PAGE_SIZE} disabled>
          <option value={DEFAULT_PAGE_SIZE}>100</option>
        </select>
      </label>

      <button className="primary-action" type="button">
        <FlaskConical size={16} aria-hidden="true" />
        Start distillation
      </button>
    </section>
  )
}

function StatsStrip({ stats }: { stats: ReturnType<typeof summarizeLabels> }) {
  return (
    <section className="stats-strip" aria-label="Label stats">
      <StatItem label="Labeled" value={stats.labeled} />
      <StatItem label="Signals" value={stats.signals} tone="success" />
      <StatItem label="Non-signals" value={stats.nonSignals} tone="warning" />
      <StatItem label="Unlabeled" value={stats.unlabeled} />
    </section>
  )
}

function StatItem({
  label,
  tone = "neutral",
  value,
}: {
  label: string
  tone?: "neutral" | "success" | "warning"
  value: number
}) {
  return (
    <div className={`stat-item stat-item-${tone}`}>
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  )
}

function ReaderControls({
  filter,
  onFilterChange,
  onSearchChange,
  searchQuery,
}: {
  filter: MessageFilter
  onFilterChange: (value: MessageFilter) => void
  onSearchChange: (value: string) => void
  searchQuery: string
}) {
  return (
    <section className="reader-controls" aria-label="Message controls">
      <label className="filter-field">
        <span>
          <SlidersHorizontal size={15} aria-hidden="true" />
          Filter
        </span>
        <select
          aria-label="Message filter"
          value={filter}
          onChange={(event) => onFilterChange(event.target.value as MessageFilter)}
        >
          <option value="all">All</option>
          <option value="candidates">Candidates</option>
          <option value="non_candidates">Non-candidates</option>
          <option value="unlabeled">Unlabeled</option>
          <option value="signal">Signal</option>
          <option value="non_signal">Non-signal</option>
          <option value="media">Has media</option>
          <option value="replies">Replies</option>
        </select>
      </label>

      <div className="active-chip" aria-label="Active filter">
        {filterLabel(filter)}
      </div>

      <label className="search-field">
        <Search size={16} aria-hidden="true" />
        <input
          aria-label="Search messages"
          placeholder="Search messages..."
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <kbd>⌘K</kbd>
      </label>
    </section>
  )
}

function MessageTable({
  messages,
  onLabelMessage,
}: {
  messages: SourceMessage[]
  onLabelMessage: (messageId: string, label: LabelValue) => void
}) {
  return (
    <section className="message-table" aria-label="Messages">
      <div className="message-header" role="row">
        <span>Source msg id</span>
        <span>Captured</span>
        <span>Posted</span>
        <span>Type</span>
        <span>Message</span>
        <span>Label</span>
      </div>
      {messages.map((message) => (
        <MessageRow
          key={message.id}
          message={message}
          onLabelMessage={onLabelMessage}
        />
      ))}
    </section>
  )
}

function MessageRow({
  message,
  onLabelMessage,
}: {
  message: SourceMessage
  onLabelMessage: (messageId: string, label: LabelValue) => void
}) {
  return (
    <article className="message-row" role="row" aria-label={`Source message ${message.sourceMessageId}`}>
      <div className="mono-cell message-id">
        <strong>{message.sourceMessageId}</strong>
        <span>{message.id}</span>
      </div>
      <time className="mono-cell" dateTime={message.capturedAt}>
        {formatDateTime(message.capturedAt)}
      </time>
      <time className="mono-cell" dateTime={message.postedAt}>
        {formatDateTime(message.postedAt)}
      </time>
      <MessageTypeIcon message={message} />
      <div className="message-body">
        <p>{message.text}</p>
        {message.isCandidate && <span className="candidate-chip">Candidate</span>}
      </div>
      <div className="label-cell">
        <span className={`label-state ${message.label ?? "unlabeled"}`}>
          {labelText(message.label)}
        </span>
        <div className="label-actions" aria-label="Label actions">
          <button
            className="label-button label-button-signal"
            type="button"
            aria-pressed={message.label === "signal"}
            aria-label="Mark as Signal"
            onClick={() => onLabelMessage(message.id, "signal")}
          >
            <TrendingUp size={14} aria-hidden="true" />
            Signal
          </button>
          <button
            className="label-button label-button-non-signal"
            type="button"
            aria-pressed={message.label === "non_signal"}
            aria-label="Mark as Non-signal"
            onClick={() => onLabelMessage(message.id, "non_signal")}
          >
            Non-signal
          </button>
        </div>
      </div>
    </article>
  )
}

function MessageTypeIcon({ message }: { message: SourceMessage }) {
  if (message.hasMedia) {
    return (
      <span className="type-icon" title="Media message">
        <ImageIcon size={15} aria-hidden="true" />
      </span>
    )
  }

  return (
    <span className="type-icon" title={message.isReply ? "Reply message" : "Text message"}>
      <MessageSquare size={15} aria-hidden="true" />
    </span>
  )
}

function Pagination({
  end,
  onNext,
  onPrevious,
  page,
  pageCount,
  pageSize,
  start,
  total,
}: {
  end: number
  onNext: () => void
  onPrevious: () => void
  page: number
  pageCount: number
  pageSize: number
  start: number
  total: number
}) {
  return (
    <nav className="pagination" aria-label="Message pagination">
      <button type="button" onClick={onPrevious} disabled={page <= 1}>
        <ChevronLeft size={16} aria-hidden="true" />
        Previous
      </button>
      <span>
        Showing {formatNumber(start)}-{formatNumber(end)} of {formatNumber(total)}
      </span>
      <span>
        Page {formatNumber(page)} of {formatNumber(pageCount)} ({pageSize} per page)
      </span>
      <button type="button" onClick={onNext} disabled={page >= pageCount}>
        Next
        <ChevronRight size={16} aria-hidden="true" />
      </button>
    </nav>
  )
}

function makeSourceMessages(): SourceMessage[] {
  const samples = [
    "$BTC breaking above 69.5k with strong volume. Next targets: 71k / 72.5k / 75k",
    "Chart update, liquidity sweep completed before NY open.",
    "Replying to @TraderMax. Agree, risk management first.",
    "Reminder: do not overleverage into news.",
    "ETH short setup forming, wait for retest before entry.",
    "SOL long entry 140 sl 135 tp 160",
    "BTC long entry 65000 sl 64000 tp 67000",
    "Morning notes, macro calendar is heavy today.",
    "AVAX buy now market order, stop under local low.",
    "LINK long entry 18 tp 22",
  ]

  return Array.from({ length: 240 }, (_, index) => {
    const sequence = index + 1
    const postedAt = new Date(Date.UTC(2026, 5, 4, 9, sequence % 60, 0))
    const capturedAt = new Date(postedAt.getTime() + 75_000)
    const initialLabel = initialMessageLabel(sequence)

    return {
      id: `msg_${String(sequence).padStart(4, "0")}`,
      sourceMessageId: String(13_485_290_000 + sequence),
      capturedAt: capturedAt.toISOString(),
      postedAt: postedAt.toISOString(),
      text: samples[index % samples.length],
      hasMedia: index % 9 === 1,
      isReply: index % 11 === 2,
      isCandidate: index % 3 !== 1,
      ...(initialLabel ? { label: initialLabel } : {}),
    }
  })
}

function initialMessageLabel(sequence: number): LabelValue | undefined {
  if (sequence <= 12) {
    return "signal"
  }

  if (sequence <= 24) {
    return "non_signal"
  }

  return undefined
}

function filterLabel(filter: MessageFilter): string {
  const labels: Record<MessageFilter, string> = {
    all: "All",
    candidates: "Candidates",
    non_candidates: "Non-candidates",
    unlabeled: "Unlabeled",
    signal: "Signal",
    non_signal: "Non-signal",
    media: "Has media",
    replies: "Replies",
  }

  return labels[filter]
}

function labelText(label: LabelValue | undefined): string {
  if (label === "signal") {
    return "Signal"
  }

  if (label === "non_signal") {
    return "Non-signal"
  }

  return "Unlabeled"
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
  }).format(date)
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value)
}

export default App
