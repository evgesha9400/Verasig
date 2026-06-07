import type { SourceType } from "./sourceLabeling"

export type BackfillStatus = "idle" | "running" | "complete" | "failed"

export type SourceChat = {
  id: string
  sourceType: SourceType
  channelId: string
  title: string
  handle: string | null
  isPrivate: boolean
  subscriberCount: number
  estimatedMessageCount: number
  capturedCount: number
  capturedThroughMessageId: string | null
  status: BackfillStatus
  failureReason?: string
}

export type ChatSummary = {
  total: number
  backfilled: number
  pending: number
  capturedTotal: number
}

export type BackfillProgress = {
  ratio: number
  percent: number
  captured: number
  estimated: number
  remaining: number
}

export function summarizeChats(chats: SourceChat[]): ChatSummary {
  const backfilled = chats.filter(isBackfilled).length

  return {
    total: chats.length,
    backfilled,
    pending: chats.length - backfilled,
    capturedTotal: chats.reduce((sum, chat) => sum + chat.capturedCount, 0),
  }
}

export function findRunningChat(chats: SourceChat[]): SourceChat | undefined {
  return chats.find((chat) => chat.status === "running")
}

export function isBackfillActive(chats: SourceChat[]): boolean {
  return findRunningChat(chats) !== undefined
}

export function findChatById(
  chats: SourceChat[],
  chatId: string,
): SourceChat | undefined {
  return chats.find((chat) => chat.id === chatId)
}

export function startBackfill(chats: SourceChat[], chatId: string): SourceChat[] {
  if (isBackfillActive(chats)) {
    return chats
  }

  return chats.map((chat) => startMatchingChat(chat, chatId))
}

export function cancelBackfill(chats: SourceChat[], chatId: string): SourceChat[] {
  return chats.map((chat) => cancelMatchingChat(chat, chatId))
}

export function advanceBackfill(
  chats: SourceChat[],
  chatId: string,
  capturedDelta: number,
): SourceChat[] {
  return chats.map((chat) => advanceMatchingChat(chat, chatId, capturedDelta))
}

export function progressOf(chat: SourceChat): BackfillProgress {
  const estimated = Math.max(chat.estimatedMessageCount, 1)
  const captured = Math.min(Math.max(chat.capturedCount, 0), estimated)
  const ratio = captured / estimated

  return {
    ratio,
    percent: Math.round(ratio * 100),
    captured,
    estimated,
    remaining: Math.max(estimated - captured, 0),
  }
}

export function estimateSecondsRemaining(
  chat: SourceChat,
  messagesPerSecond: number,
): number {
  if (messagesPerSecond <= 0) {
    return 0
  }

  return Math.ceil(progressOf(chat).remaining / messagesPerSecond)
}

export function isBackfilled(chat: SourceChat): boolean {
  return chat.status === "complete"
}

export function isResumable(chat: SourceChat): boolean {
  return chat.status === "idle" && chat.capturedCount > 0
}

export function canStartBackfill(chat: SourceChat): boolean {
  return chat.status === "idle" || chat.status === "failed"
}

function startMatchingChat(chat: SourceChat, chatId: string): SourceChat {
  if (chat.id !== chatId || !canStartBackfill(chat)) {
    return chat
  }

  return { ...chat, status: "running" }
}

function cancelMatchingChat(chat: SourceChat, chatId: string): SourceChat {
  if (chat.id !== chatId || chat.status !== "running") {
    return chat
  }

  return { ...chat, status: "idle" }
}

function advanceMatchingChat(
  chat: SourceChat,
  chatId: string,
  capturedDelta: number,
): SourceChat {
  if (chat.id !== chatId || chat.status !== "running") {
    return chat
  }

  const captured = Math.min(
    chat.capturedCount + Math.max(capturedDelta, 0),
    chat.estimatedMessageCount,
  )

  if (captured >= chat.estimatedMessageCount) {
    return completeChat(chat)
  }

  return { ...chat, capturedCount: captured }
}

function completeChat(chat: SourceChat): SourceChat {
  return {
    ...chat,
    status: "complete",
    capturedCount: chat.estimatedMessageCount,
    capturedThroughMessageId: makeCapturedThroughId(chat),
  }
}

function makeCapturedThroughId(chat: SourceChat): string {
  return String(Number(chat.channelId) + chat.estimatedMessageCount)
}
