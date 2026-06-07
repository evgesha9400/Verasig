import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Search,
  Send,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react"
import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react"
import { tokenizeMessage, type MessageToken } from "./messageMarkup"
import type { SourceChat } from "./sourceChats"
import {
  DEFAULT_PAGE_SIZE,
  filterMessages,
  labelMessage,
  paginateMessages,
  sortMessagesNewestFirst,
  summarizeLabels,
  type LabelValue,
  type MessageFilter,
  type SourceMessage,
} from "./sourceLabeling"

type MessageFilterOption = {
  label: string
  value: MessageFilter
}

const defaultMessageFilterOption: MessageFilterOption = {
  label: "All",
  value: "all",
}

const messageFilterOptions: MessageFilterOption[] = [
  defaultMessageFilterOption,
  { label: "Candidates", value: "candidates" },
  { label: "Non-candidates", value: "non_candidates" },
  { label: "Unlabeled", value: "unlabeled" },
  { label: "Signal", value: "signal" },
  { label: "Non-signal", value: "non_signal" },
  { label: "Has media", value: "media" },
  { label: "Replies", value: "replies" },
]

function ReaderPage({ chat, onBack }: { chat: SourceChat; onBack: () => void }) {
  const [messages, setMessages] = useState(makeSourceMessages)
  const [filter, setFilter] = useState<MessageFilter>("unlabeled")
  const [searchQuery, setSearchQuery] = useState("")
  const [page, setPage] = useState(1)
  const [activeMessageId, setActiveMessageId] = useState<string | undefined>()

  const sortedMessages = useMemo(
    () => sortMessagesNewestFirst(messages),
    [messages],
  )
  const visibleMessages = useMemo(
    () => filterMessages(sortedMessages, filter, searchQuery),
    [filter, searchQuery, sortedMessages],
  )
  const pageSlice = useMemo(
    () => paginateMessages(visibleMessages, page, DEFAULT_PAGE_SIZE),
    [page, visibleMessages],
  )
  const stats = summarizeLabels(messages)
  const activePageMessageId = selectActivePageMessageId(
    activeMessageId,
    pageSlice.items,
  )

  useEffect(() => {
    function handleWindowKeyDown(event: KeyboardEvent) {
      if (targetConsumesReaderShortcut(event.target)) {
        return
      }

      if (event.altKey || event.ctrlKey || event.metaKey) {
        return
      }

      if (event.key === "ArrowDown" || event.key.toLowerCase() === "j") {
        event.preventDefault()
        setActiveMessageId(
          adjacentMessageId(pageSlice.items, activePageMessageId, 1),
        )
        return
      }

      if (event.key === "ArrowUp" || event.key.toLowerCase() === "k") {
        event.preventDefault()
        setActiveMessageId(
          adjacentMessageId(pageSlice.items, activePageMessageId, -1),
        )
        return
      }

      if (event.key.toLowerCase() === "s") {
        event.preventDefault()
        labelMessageWithShortcut("signal")
        return
      }

      if (event.key.toLowerCase() === "n") {
        event.preventDefault()
        labelMessageWithShortcut("non_signal")
      }
    }

    function labelMessageWithShortcut(label: LabelValue) {
      if (!activePageMessageId) {
        return
      }

      setMessages((currentMessages) =>
        labelMessage(currentMessages, activePageMessageId, label),
      )
      setActiveMessageId(nextMessageIdAfter(pageSlice.items, activePageMessageId))
    }

    window.addEventListener("keydown", handleWindowKeyDown)

    return () => {
      window.removeEventListener("keydown", handleWindowKeyDown)
    }
  }, [activePageMessageId, pageSlice.items])

  function saveMessageLabel(messageId: string, label: LabelValue) {
    setMessages((currentMessages) => labelMessage(currentMessages, messageId, label))
    setActiveMessageId(nextMessageIdAfter(pageSlice.items, messageId))
  }

  function selectMessageFilter(value: MessageFilter) {
    setFilter(value)
    setPage(1)
    setActiveMessageId(undefined)
  }

  function updateSearchQuery(value: string) {
    setSearchQuery(value)
    setPage(1)
    setActiveMessageId(undefined)
  }

  function selectActiveMessage(messageId: string) {
    setActiveMessageId(messageId)
  }

  return (
    <section className="reader-frame" aria-label="Source labeling reader">
      <ReaderBreadcrumb chat={chat} onBack={onBack} />
      <ReaderHeader chat={chat} stats={stats}>
        <ReaderControls
          filter={filter}
          onFilterChange={selectMessageFilter}
          searchQuery={searchQuery}
          onSearchChange={updateSearchQuery}
        />
      </ReaderHeader>
      <MessageStream
        activeMessageId={activePageMessageId}
        messages={pageSlice.items}
        onActivateMessage={selectActiveMessage}
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
  )
}

function ReaderBreadcrumb({
  chat,
  onBack,
}: {
  chat: SourceChat
  onBack: () => void
}) {
  return (
    <nav className="reader-breadcrumb" aria-label="Breadcrumb">
      <button className="breadcrumb-back" type="button" onClick={onBack}>
        <ChevronLeft size={15} aria-hidden="true" />
        Sources
      </button>
      <span className="breadcrumb-sep" aria-hidden="true">
        /
      </span>
      <span aria-current="page" className="breadcrumb-current">
        {chat.title}
      </span>
    </nav>
  )
}

function ReaderHeader({
  chat,
  stats,
  children,
}: {
  chat: SourceChat
  stats: ReturnType<typeof summarizeLabels>
  children: ReactNode
}) {
  return (
    <header className="reader-head">
      <div className="reader-head-top">
        <div className="reader-source">
          <span className="reader-source-mark" aria-hidden="true">
            <Send size={18} strokeWidth={2.2} />
          </span>
          <div className="reader-source-text">
            <h2 className="reader-source-title">
              {chat.title}
              <span className="reader-platform">Telegram</span>
            </h2>
            <p className="reader-source-sub">
              <span className="reader-handle">
                {chat.handle ?? "Private channel"}
              </span>
              <span className="reader-dot" aria-hidden="true">
                ·
              </span>
              <span className="reader-complete">
                <Check size={14} aria-hidden="true" />
                backfill complete
              </span>
              <span className="reader-dot" aria-hidden="true">
                ·
              </span>
              <span>{formatNumber(chat.capturedCount)} captured</span>
            </p>
          </div>
        </div>

        <div className="reader-stats" aria-label="Label stats">
          <div className="reader-stats-head">
            <span className="reader-stats-count">
              <b>{formatNumber(stats.labeled)}</b> labeled{" "}
              <span>of {formatNumber(stats.total)}</span>
            </span>
            <button className="reader-distill" type="button">
              <FlaskConical size={14} aria-hidden="true" />
              Start distillation
            </button>
          </div>
          <LabelMeter
            nonSignals={stats.nonSignals}
            signals={stats.signals}
            total={stats.total}
          />
          <ul className="reader-legend">
            <LegendItem tone="signal" value={stats.signals} label="signals" />
            <LegendItem tone="nonsignal" value={stats.nonSignals} label="non-signals" />
            <LegendItem tone="unlabeled" value={stats.unlabeled} label="unlabeled" />
          </ul>
        </div>
      </div>

      {children}
    </header>
  )
}

function LabelMeter({
  nonSignals,
  signals,
  total,
}: {
  nonSignals: number
  signals: number
  total: number
}) {
  const unlabeled = total - signals - nonSignals

  return (
    <div
      className="label-meter"
      role="img"
      aria-label={`${signals} signal, ${nonSignals} non-signal, ${unlabeled} unlabeled of ${total}`}
    >
      <span className="seg-signal" style={{ width: percentOf(signals, total) }} />
      <span
        className="seg-nonsignal"
        style={{ width: percentOf(nonSignals, total) }}
      />
    </div>
  )
}

function LegendItem({
  label,
  tone,
  value,
}: {
  label: string
  tone: "signal" | "nonsignal" | "unlabeled"
  value: number
}) {
  return (
    <li>
      <span className={`legend-dot legend-${tone}`} aria-hidden="true" />
      <b>{formatNumber(value)}</b> {label}
    </li>
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
  const filterMenuId = useId()
  const filterMenuRef = useRef<HTMLDivElement>(null)
  const [isFilterMenuOpen, setFilterMenuOpen] = useState(false)
  const selectedFilterOption = selectMessageFilterOption(filter)

  useEffect(() => {
    if (!isFilterMenuOpen) {
      return
    }

    function closeFilterMenuWhenPointerStartsOutside(event: PointerEvent) {
      if (targetIsInsideElement(filterMenuRef.current, event.target)) {
        return
      }

      setFilterMenuOpen(false)
    }

    document.addEventListener("pointerdown", closeFilterMenuWhenPointerStartsOutside)

    return () => {
      document.removeEventListener(
        "pointerdown",
        closeFilterMenuWhenPointerStartsOutside,
      )
    }
  }, [isFilterMenuOpen])

  function toggleFilterMenu() {
    setFilterMenuOpen((currentValue) => !currentValue)
  }

  function closeFilterMenu() {
    setFilterMenuOpen(false)
  }

  function closeFilterMenuWhenEscapeIsPressed(
    event: ReactKeyboardEvent<HTMLDivElement>,
  ) {
    if (event.key !== "Escape") {
      return
    }

    event.preventDefault()
    closeFilterMenu()
  }

  function selectFilterOption(value: MessageFilter) {
    onFilterChange(value)
    closeFilterMenu()
  }

  return (
    <section className="reader-controls" aria-label="Message controls">
      <label className="search-field" aria-label="Search messages">
        <Search size={16} aria-hidden="true" />
        <input
          aria-label="Search messages"
          placeholder="Search messages..."
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>

      <div
        className="filter-menu-wrapper"
        onKeyDown={closeFilterMenuWhenEscapeIsPressed}
        ref={filterMenuRef}
      >
        <button
          aria-controls={filterMenuId}
          aria-expanded={isFilterMenuOpen}
          aria-haspopup="listbox"
          aria-label={`Message filter: ${selectedFilterOption.label}`}
          className="filter-trigger"
          type="button"
          onClick={toggleFilterMenu}
        >
          <span className="filter-trigger-label">
            <SlidersHorizontal size={15} aria-hidden="true" />
            Filter
          </span>
          <span className="filter-trigger-value">{selectedFilterOption.label}</span>
          <ChevronDown
            className="filter-trigger-chevron"
            size={15}
            aria-hidden="true"
          />
        </button>

        {isFilterMenuOpen && (
          <div
            aria-label="Message filter options"
            className="filter-popover"
            id={filterMenuId}
            role="listbox"
          >
            {messageFilterOptions.map((option) => (
              <button
                aria-selected={option.value === filter}
                className="filter-option"
                key={option.value}
                role="option"
                type="button"
                onClick={() => selectFilterOption(option.value)}
              >
                <span>{option.label}</span>
                {option.value === filter && <Check size={14} aria-hidden="true" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function MessageStream({
  activeMessageId,
  messages,
  onActivateMessage,
  onLabelMessage,
}: {
  activeMessageId: string | undefined
  messages: SourceMessage[]
  onActivateMessage: (messageId: string) => void
  onLabelMessage: (messageId: string, label: LabelValue) => void
}) {
  return (
    <section className="stream" aria-label="Messages">
      {messages.map((message) => (
        <MessageEntry
          isActive={message.id === activeMessageId}
          key={message.id}
          message={message}
          onActivateMessage={onActivateMessage}
          onLabelMessage={onLabelMessage}
        />
      ))}
    </section>
  )
}

function MessageEntry({
  isActive,
  message,
  onActivateMessage,
  onLabelMessage,
}: {
  isActive: boolean
  message: SourceMessage
  onActivateMessage: (messageId: string) => void
  onLabelMessage: (messageId: string, label: LabelValue) => void
}) {
  const labelClass = message.label ?? "unlabeled"

  return (
    <article
      aria-current={isActive ? "true" : "false"}
      aria-label={`Source message ${message.sourceMessageId}`}
      className={`entry entry-${labelClass}`}
      onClick={() => onActivateMessage(message.id)}
      role="article"
      tabIndex={isActive ? 0 : -1}
    >
      <header className="entry-head">
        <div className="entry-meta">
          <span className={`entry-dot dot-${labelClass}`} aria-hidden="true" />
          <span className="entry-id">{message.sourceMessageId}</span>
          <span className="entry-sep" aria-hidden="true">
            ·
          </span>
          <time className="entry-time" dateTime={message.postedAt}>
            {formatDateTime(message.postedAt)}
          </time>
          {message.isCandidate && <span className="candidate-chip">Candidate</span>}
          <MessageTypeTag message={message} />
        </div>
        <div className="label-actions" aria-label="Label actions">
          <span className={`label-state ${labelClass}`}>{labelText(message.label)}</span>
          <button
            className="label-button label-button-signal"
            type="button"
            aria-pressed={message.label === "signal"}
            aria-label="Mark as Signal"
            onClick={(event) => {
              event.stopPropagation()
              onLabelMessage(message.id, "signal")
            }}
          >
            <TrendingUp size={14} aria-hidden="true" />
            Signal
          </button>
          <button
            className="label-button label-button-non-signal"
            type="button"
            aria-pressed={message.label === "non_signal"}
            aria-label="Mark as Non-signal"
            onClick={(event) => {
              event.stopPropagation()
              onLabelMessage(message.id, "non_signal")
            }}
          >
            Non-signal
          </button>
        </div>
      </header>
      <p className="raw">{renderMessageBody(message.text)}</p>
    </article>
  )
}

function MessageTypeTag({ message }: { message: SourceMessage }) {
  if (message.hasMedia) {
    return <span className="entry-tag">Media</span>
  }

  if (message.isReply) {
    return <span className="entry-tag">Reply</span>
  }

  return null
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

function renderMessageBody(text: string): ReactNode[] {
  return tokenizeMessage(text).map((token, index) => renderToken(token, index))
}

function renderToken(token: MessageToken, index: number): ReactNode {
  if (token.type === "text") {
    return token.value
  }

  return (
    <span className={`tok-${token.type}`} key={index}>
      {token.value}
    </span>
  )
}

function makeSourceMessages(): SourceMessage[] {
  const samples = makeTelegramSignalSamples()

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

function makeTelegramSignalSamples(): string[] {
  return [
    `Image
🪙 МОНЕТА: #ENA/USDT

📉📈ПОКУПКА: SHORT
ПЛЕЧО: 16x

· Вход: 0.09109$

· Фиксируем прибыль на: 0.08994$ 0.08844$ 0.08680$ 0.08509$ 0.08330$ 0.08191$

· Стоп: 0.09925$
Вы самостоятельно решаете когда фиксировать прибыль❗️
➿➿➿➿➿➿➿➿➿➿➿
• Даю бесплатные прибыльные сигналы - МатематикТорговля
• Отзывы совместной работы от подписчиков - МатематикОтзывы
• Моё закрытое трейдинг сообщество - МатематикВип`,
    `Image
🪙 МОНЕТА: #BTC/USDT

📉📈ПОКУПКА: LONG
ПЛЕЧО: 10x

· Вход: 67,180$

· Фиксируем прибыль на: 67,920$ 68,450$ 69,100$ 70,000$

· Стоп: 66,420$
Переносим стоп после первой фиксации прибыли.`,
    `#ETH/USDT SHORT

Entry: 3,514-3,529
Leverage: 12x

Targets: 3,482 / 3,448 / 3,401 / 3,360
Stop: 3,612

Wait for confirmation candle before entering.`,
    `Quick update

#SOL/USDT remains a candidate.
No entry yet.

Breakout level: 164.80
Invalidation: close below 158.20`,
    `Replying to @TraderMax

The setup is still valid.
I would not add size before the retest.
Risk stays 1 percent maximum.`,
    `Image
#AVAX/USDT LONG

Entry: 29.40
Targets: 30.10 / 30.80 / 31.90
Stop: 28.30

Volume confirmation is required.`,
    `Market note

BTC dominance is rising.
Avoid weak alt entries until liquidity rotates back.`,
    `#LINK/USDT LONG

Entry: 18.20-18.35
Targets: 18.90 / 19.45 / 20.10
Stop: 17.74

Do not enter after target 1.`,
  ]
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

function labelText(label: LabelValue | undefined): string {
  if (label === "signal") {
    return "Signal"
  }

  if (label === "non_signal") {
    return "Non-signal"
  }

  return "Unlabeled"
}

function selectMessageFilterOption(filter: MessageFilter): MessageFilterOption {
  return (
    messageFilterOptions.find((option) => option.value === filter) ??
    defaultMessageFilterOption
  )
}

function targetIsInsideElement(
  element: HTMLElement | null,
  target: EventTarget | null,
): boolean {
  return element !== null && target instanceof Node && element.contains(target)
}

function selectActivePageMessageId(
  activeMessageId: string | undefined,
  messages: SourceMessage[],
): string | undefined {
  if (messages.length === 0) {
    return undefined
  }

  if (activeMessageId && messages.some((message) => message.id === activeMessageId)) {
    return activeMessageId
  }

  return messages[0].id
}

function adjacentMessageId(
  messages: SourceMessage[],
  activeMessageId: string | undefined,
  offset: number,
): string | undefined {
  if (messages.length === 0) {
    return undefined
  }

  const activeIndex = Math.max(
    0,
    messages.findIndex((message) => message.id === activeMessageId),
  )
  const nextIndex = clampIndex(activeIndex + offset, messages.length)

  return messages[nextIndex].id
}

function nextMessageIdAfter(
  messages: SourceMessage[],
  messageId: string,
): string | undefined {
  if (messages.length === 0) {
    return undefined
  }

  const currentIndex = messages.findIndex((message) => message.id === messageId)
  if (currentIndex < 0) {
    return messages[0].id
  }

  const nextIndex = Math.min(currentIndex + 1, messages.length - 1)
  return messages[nextIndex]?.id
}

function clampIndex(index: number, length: number): number {
  return Math.min(Math.max(index, 0), length - 1)
}

function targetConsumesReaderShortcut(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  if (target.isContentEditable) {
    return true
  }

  return ["BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
}

function percentOf(value: number, total: number): string {
  if (total <= 0) {
    return "0%"
  }

  return `${(value / total) * 100}%`
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

export default ReaderPage
