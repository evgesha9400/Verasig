export type SourceType = "telegram"

export type LabelValue = "signal" | "non_signal"

export type MessageFilter =
  | "all"
  | "candidates"
  | "non_candidates"
  | "unlabeled"
  | "signal"
  | "non_signal"
  | "media"
  | "replies"

export type SourceFeed = {
  id: string
  sourceType: SourceType
  name: string
  handle: string
  capturedCount: number
  backfillStatus: "idle" | "running" | "complete" | "failed"
}

export type SourceMessage = {
  id: string
  sourceMessageId: string
  capturedAt: string
  postedAt: string
  text: string
  hasMedia: boolean
  isReply: boolean
  isCandidate: boolean
  label?: LabelValue
}

export type LabelStats = {
  total: number
  labeled: number
  signals: number
  nonSignals: number
  unlabeled: number
}

export type PageSlice<T> = {
  items: T[]
  page: number
  pageSize: number
  pageCount: number
  total: number
  start: number
  end: number
}

export const DEFAULT_PAGE_SIZE = 100

export function summarizeLabels(messages: SourceMessage[]): LabelStats {
  const signals = countMessagesWithLabel(messages, "signal")
  const nonSignals = countMessagesWithLabel(messages, "non_signal")
  const labeled = signals + nonSignals

  return {
    total: messages.length,
    labeled,
    signals,
    nonSignals,
    unlabeled: messages.length - labeled,
  }
}

export function sortMessagesNewestFirst(messages: SourceMessage[]): SourceMessage[] {
  return [...messages].sort(compareNewestPostedMessageFirst)
}

export function filterMessages(
  messages: SourceMessage[],
  filter: MessageFilter,
  searchQuery: string,
): SourceMessage[] {
  return messages
    .filter((message) => messageMatchesFilter(message, filter))
    .filter((message) => messageMatchesSearch(message, searchQuery))
}

export function paginateMessages<T>(
  items: T[],
  page: number,
  pageSize = DEFAULT_PAGE_SIZE,
): PageSlice<T> {
  const total = items.length
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const safePage = clampPage(page, pageCount)
  const startIndex = (safePage - 1) * pageSize
  const pageItems = items.slice(startIndex, startIndex + pageSize)

  return {
    items: pageItems,
    page: safePage,
    pageSize,
    pageCount,
    total,
    start: pageItems.length === 0 ? 0 : startIndex + 1,
    end: startIndex + pageItems.length,
  }
}

export function labelMessage(
  messages: SourceMessage[],
  messageId: string,
  label: LabelValue,
): SourceMessage[] {
  return messages.map((message) => labelMatchingMessage(message, messageId, label))
}

function countMessagesWithLabel(
  messages: SourceMessage[],
  label: LabelValue,
): number {
  return messages.filter((message) => message.label === label).length
}

function compareNewestPostedMessageFirst(
  left: SourceMessage,
  right: SourceMessage,
): number {
  return Date.parse(right.postedAt) - Date.parse(left.postedAt)
}

function messageMatchesFilter(
  message: SourceMessage,
  filter: MessageFilter,
): boolean {
  if (filter === "all") {
    return true
  }

  if (filter === "candidates") {
    return message.isCandidate
  }

  if (filter === "non_candidates") {
    return !message.isCandidate
  }

  if (filter === "unlabeled") {
    return message.label === undefined
  }

  if (filter === "signal") {
    return message.label === "signal"
  }

  if (filter === "non_signal") {
    return message.label === "non_signal"
  }

  if (filter === "media") {
    return message.hasMedia
  }

  return message.isReply
}

function messageMatchesSearch(
  message: SourceMessage,
  searchQuery: string,
): boolean {
  const query = searchQuery.trim().toLowerCase()
  if (!query) {
    return true
  }

  return message.text.toLowerCase().includes(query)
}

function clampPage(page: number, pageCount: number): number {
  return Math.min(Math.max(1, page), pageCount)
}

function labelMatchingMessage(
  message: SourceMessage,
  messageId: string,
  label: LabelValue,
): SourceMessage {
  if (message.id !== messageId) {
    return message
  }

  return { ...message, label }
}
