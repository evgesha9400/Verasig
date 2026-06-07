import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import ChatsPage from "./ChatsPage"
import type { ChatSummary, SourceChat } from "./sourceChats"

function makeChat(overrides: Partial<SourceChat> = {}): SourceChat {
  return {
    id: "chat_x",
    sourceType: "telegram",
    channelId: "1000000001",
    title: "Test Chat",
    handle: "@test",
    isPrivate: false,
    subscriberCount: 1_000,
    estimatedMessageCount: 1_000,
    capturedCount: 0,
    capturedThroughMessageId: null,
    status: "idle",
    ...overrides,
  }
}

const completeChat = makeChat({
  id: "c1",
  title: "Crypto Alpha Signals",
  handle: "@cryptoalphasignals",
  status: "complete",
  capturedCount: 152_842,
  estimatedMessageCount: 152_842,
})
const idleChat = makeChat({
  id: "c2",
  title: "Whale Pump Alerts",
  handle: "@whalepump",
})
const privateChat = makeChat({
  id: "c3",
  title: "Математик Торговля",
  handle: null,
  isPrivate: true,
})
const runningChat = makeChat({
  id: "c4",
  title: "Futures Sniper",
  status: "running",
  capturedCount: 600,
  estimatedMessageCount: 1_000,
})
const failedChat = makeChat({
  id: "c5",
  title: "BlackBox VIP",
  handle: null,
  isPrivate: true,
  status: "failed",
  failureReason: "Flood-wait limit reached at message 4,120",
  capturedCount: 4_120,
})
const resumableChat = makeChat({
  id: "c6",
  title: "Scalp Room",
  status: "idle",
  capturedCount: 300,
  estimatedMessageCount: 1_000,
})

const emptySummary: ChatSummary = {
  total: 0,
  backfilled: 0,
  pending: 0,
  capturedTotal: 0,
}

type ChatsProps = Parameters<typeof ChatsPage>[0]

function renderChats(overrides: Partial<ChatsProps> = {}) {
  const props: ChatsProps = {
    visibleChats: [],
    totalChats: 0,
    summary: emptySummary,
    loading: false,
    runningChat: undefined,
    secondsRemaining: 0,
    searchQuery: "",
    onSearchChange: vi.fn(),
    onStartBackfill: vi.fn(),
    onCancelBackfill: vi.fn(),
    ...overrides,
  }
  render(<ChatsPage {...props} />)
  return props
}

describe("telegram chats page", () => {
  it("renders one row per chat with its handle or private marker", () => {
    renderChats({ visibleChats: [completeChat, idleChat, privateChat], totalChats: 3 })

    expect(screen.getByRole("heading", { name: "Telegram chats" })).toBeVisible()
    expect(screen.getByText("Whale Pump Alerts")).toBeVisible()
    expect(screen.getByText("@whalepump")).toBeVisible()
    expect(screen.getByText("Private channel")).toBeVisible()
  })

  it("labels subscriber counts as a proxy, never a quality claim", () => {
    renderChats({ visibleChats: [idleChat], totalChats: 1 })

    const proxyTag = screen.getByText("proxy")
    expect(proxyTag).toHaveAttribute("title", expect.stringContaining("proxy"))
  })

  it("links a backfilled chat straight to its reader route", () => {
    renderChats({ visibleChats: [completeChat], totalChats: 1 })

    expect(screen.getByRole("link", { name: /open reader/i })).toHaveAttribute(
      "href",
      "#/reader/c1",
    )
  })

  it("starts a backfill for an idle chat", async () => {
    const user = userEvent.setup()
    const props = renderChats({ visibleChats: [idleChat], totalChats: 1 })

    await user.click(screen.getByRole("button", { name: "Start backfill" }))

    expect(props.onStartBackfill).toHaveBeenCalledWith("c2")
  })

  it("blocks starting any other backfill while one is running", () => {
    renderChats({
      visibleChats: [runningChat, idleChat, failedChat, resumableChat],
      totalChats: 4,
      runningChat,
    })

    expect(screen.getByRole("button", { name: "Start backfill" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Retry" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Resume backfill" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Start backfill" })).toHaveAttribute(
      "title",
      "Finish or cancel the active backfill first",
    )
  })

  it("shows determinate progress and a cancel control for a running chat", async () => {
    const user = userEvent.setup()
    const props = renderChats({ visibleChats: [runningChat], totalChats: 1 })

    const rowProgress = screen.getByRole("progressbar")
    expect(rowProgress).toHaveAttribute("aria-valuenow", "60")

    await user.click(screen.getByRole("button", { name: /cancel/i }))
    expect(props.onCancelBackfill).toHaveBeenCalledWith("c4")
  })

  it("surfaces the failure reason and a retry for a failed chat", () => {
    renderChats({ visibleChats: [failedChat], totalChats: 1 })

    expect(screen.getByText(/flood-wait limit reached/i)).toBeVisible()
    expect(screen.getByRole("button", { name: "Retry" })).toBeVisible()
  })

  it("marks a resumable chat as paused with a resume action", () => {
    renderChats({ visibleChats: [resumableChat], totalChats: 1 })

    expect(screen.getByText("Paused")).toBeVisible()
    expect(screen.getByRole("button", { name: "Resume backfill" })).toBeVisible()
  })

  it("shows skeletons while loading and no chat rows", () => {
    renderChats({ loading: true, totalChats: 4 })

    expect(screen.getByRole("status", { name: "Loading chats" })).toBeVisible()
    expect(screen.queryByRole("list", { name: "Available chats" })).not.toBeInTheDocument()
  })

  it("shows an empty state echoing the search that matched nothing", () => {
    renderChats({ visibleChats: [], totalChats: 5, searchQuery: "zzz" })

    expect(screen.getByText('No chats match "zzz"')).toBeVisible()
  })

  it("pins an active backfill summary with percent and time remaining", () => {
    renderChats({
      visibleChats: [idleChat],
      totalChats: 2,
      runningChat,
      secondsRemaining: 4,
    })

    const summary = screen.getByRole("complementary", { name: "Active backfill" })
    expect(within(summary).getByText("Futures Sniper")).toBeVisible()
    expect(within(summary).getByText("60%")).toBeVisible()
    expect(within(summary).getByText("~4s left")).toBeVisible()
  })

  it("reports the connection summary stats", () => {
    renderChats({
      visibleChats: [completeChat, idleChat],
      totalChats: 2,
      summary: { total: 2, backfilled: 1, pending: 1, capturedTotal: 152_842 },
    })

    const connection = screen.getByLabelText("Connected source")
    expect(within(connection).getByText("152,842")).toBeVisible()
  })
})
