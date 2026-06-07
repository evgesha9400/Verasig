import { describe, expect, it } from "vitest"
import {
  DEFAULT_PAGE_SIZE,
  filterMessages,
  labelMessage,
  paginateMessages,
  sortMessagesNewestFirst,
  summarizeLabels,
  type SourceMessage,
} from "./sourceLabeling"

const messages: SourceMessage[] = [
  {
    id: "m1",
    sourceMessageId: "1",
    capturedAt: "2026-06-04T12:00:00Z",
    postedAt: "2026-06-04T12:00:00Z",
    text: "BTC long entry 65000 sl 64000 tp 67000",
    hasMedia: false,
    isReply: false,
    isCandidate: true,
    label: "signal",
  },
  {
    id: "m2",
    sourceMessageId: "2",
    capturedAt: "2026-06-04T12:01:00Z",
    postedAt: "2026-06-04T12:01:00Z",
    text: "gm frens",
    hasMedia: false,
    isReply: false,
    isCandidate: false,
    label: "non_signal",
  },
  {
    id: "m3",
    sourceMessageId: "3",
    capturedAt: "2026-06-04T12:02:00Z",
    postedAt: "2026-06-04T12:02:00Z",
    text: "chart update",
    hasMedia: true,
    isReply: true,
    isCandidate: false,
  },
]

describe("source labeling state", () => {
  it("summarizes only signal and non-signal labels", () => {
    expect(summarizeLabels(messages)).toEqual({
      total: 3,
      labeled: 2,
      signals: 1,
      nonSignals: 1,
      unlabeled: 1,
    })
  })

  it("sorts messages newest first", () => {
    expect(sortMessagesNewestFirst(messages).map((message) => message.id)).toEqual([
      "m3",
      "m2",
      "m1",
    ])
  })

  it("filters candidates, non-candidates, labels, media, replies, and search", () => {
    expect(filterMessages(messages, "candidates", "").map((message) => message.id)).toEqual([
      "m1",
    ])
    expect(filterMessages(messages, "non_candidates", "").map((message) => message.id)).toEqual([
      "m2",
      "m3",
    ])
    expect(filterMessages(messages, "signal", "").map((message) => message.id)).toEqual([
      "m1",
    ])
    expect(filterMessages(messages, "non_signal", "").map((message) => message.id)).toEqual([
      "m2",
    ])
    expect(filterMessages(messages, "media", "").map((message) => message.id)).toEqual([
      "m3",
    ])
    expect(filterMessages(messages, "replies", "").map((message) => message.id)).toEqual([
      "m3",
    ])
    expect(filterMessages(messages, "all", "long").map((message) => message.id)).toEqual([
      "m1",
    ])
  })

  it("paginates with 100 items by default", () => {
    const ids = Array.from({ length: 250 }, (_, index) => index + 1)

    expect(paginateMessages(ids, 2)).toEqual({
      items: ids.slice(100, 200),
      page: 2,
      pageSize: DEFAULT_PAGE_SIZE,
      pageCount: 3,
      total: 250,
      start: 101,
      end: 200,
    })
  })

  it("updates one message label without introducing a third label state", () => {
    const updated = labelMessage(messages, "m3", "non_signal")

    expect(updated.find((message) => message.id === "m3")?.label).toBe("non_signal")
    expect(summarizeLabels(updated)).toMatchObject({
      labeled: 3,
      signals: 1,
      nonSignals: 2,
    })
  })
})
