import { describe, expect, it } from "vitest"
import {
  advanceBackfill,
  canStartBackfill,
  cancelBackfill,
  estimateSecondsRemaining,
  filterChats,
  findRunningChat,
  isBackfillActive,
  isBackfilled,
  isResumable,
  progressOf,
  startBackfill,
  summarizeChats,
  type SourceChat,
} from "./sourceChats"

function makeChat(overrides: Partial<SourceChat> = {}): SourceChat {
  return {
    id: "chat_test",
    sourceType: "telegram",
    channelId: "13485290000",
    title: "Test Chat",
    handle: "@test",
    isPrivate: false,
    subscriberCount: 1000,
    estimatedMessageCount: 1000,
    capturedCount: 0,
    capturedThroughMessageId: null,
    status: "idle",
    ...overrides,
  }
}

describe("source chats state", () => {
  it("summarizes backfilled, pending, and captured totals", () => {
    const chats = [
      makeChat({ id: "a", status: "complete", capturedCount: 1000 }),
      makeChat({ id: "b", status: "idle", capturedCount: 0 }),
      makeChat({ id: "c", status: "idle", capturedCount: 250 }),
    ]

    expect(summarizeChats(chats)).toEqual({
      total: 3,
      backfilled: 1,
      pending: 2,
      capturedTotal: 1250,
    })
  })

  it("starts a backfill on one idle chat", () => {
    const chats = [makeChat({ id: "a" }), makeChat({ id: "b" })]

    const started = startBackfill(chats, "a")

    expect(findRunningChat(started)?.id).toBe("a")
    expect(isBackfillActive(started)).toBe(true)
  })

  it("blocks a second backfill while one is already running", () => {
    const chats = [
      makeChat({ id: "a", status: "running", capturedCount: 100 }),
      makeChat({ id: "b" }),
    ]

    const started = startBackfill(chats, "b")

    expect(started).toBe(chats)
    expect(findRunningChat(started)?.id).toBe("a")
  })

  it("restarts a failed chat but never a completed one", () => {
    const chats = [
      makeChat({ id: "a", status: "failed", failureReason: "Flood-wait" }),
    ]
    expect(findRunningChat(startBackfill(chats, "a"))?.id).toBe("a")

    const done = [makeChat({ id: "a", status: "complete", capturedCount: 1000 })]
    const afterStart = startBackfill(done, "a")
    expect(findRunningChat(afterStart)).toBeUndefined()
    expect(afterStart[0].status).toBe("complete")
    expect(canStartBackfill(done[0])).toBe(false)
  })

  it("advances captured count and completes at the estimate", () => {
    const chats = [makeChat({ id: "a", status: "running", capturedCount: 0 })]

    const midway = advanceBackfill(chats, "a", 400)
    expect(progressOf(midway[0])).toMatchObject({ captured: 400, percent: 40 })
    expect(midway[0].status).toBe("running")

    const finished = advanceBackfill(midway, "a", 700)
    expect(finished[0].status).toBe("complete")
    expect(finished[0].capturedCount).toBe(1000)
    expect(finished[0].capturedThroughMessageId).not.toBeNull()
    expect(isBackfilled(finished[0])).toBe(true)
  })

  it("cancels a running backfill back to a resumable idle state", () => {
    const chats = [makeChat({ id: "a", status: "running", capturedCount: 300 })]

    const cancelled = cancelBackfill(chats, "a")

    expect(cancelled[0].status).toBe("idle")
    expect(cancelled[0].capturedCount).toBe(300)
    expect(isResumable(cancelled[0])).toBe(true)
  })

  it("reports an idle chat with zero captured as a fresh, non-resumable start", () => {
    expect(isResumable(makeChat({ status: "idle", capturedCount: 0 }))).toBe(false)
  })

  it("filters chats by title or handle and ignores empty queries", () => {
    const chats = [
      makeChat({ id: "a", title: "Whale Pump Alerts", handle: "@whalepump" }),
      makeChat({ id: "b", title: "Математик Торговля", handle: null }),
      makeChat({ id: "c", title: "Macro Desk", handle: "@macrodesk" }),
    ]

    expect(filterChats(chats, "  ").map((chat) => chat.id)).toEqual(["a", "b", "c"])
    expect(filterChats(chats, "whale").map((chat) => chat.id)).toEqual(["a"])
    expect(filterChats(chats, "@macro").map((chat) => chat.id)).toEqual(["c"])
    expect(filterChats(chats, "Математик").map((chat) => chat.id)).toEqual(["b"])
  })

  it("estimates remaining seconds from the capture rate", () => {
    const chat = makeChat({
      status: "running",
      capturedCount: 600,
      estimatedMessageCount: 1000,
    })

    expect(estimateSecondsRemaining(chat, 100)).toBe(4)
    expect(estimateSecondsRemaining(chat, 0)).toBe(0)
  })
})
