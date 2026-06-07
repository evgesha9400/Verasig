import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import ReaderPage from "./ReaderPage"
import type { SourceChat } from "./sourceChats"

const completeChat: SourceChat = {
  id: "chat_crypto_alpha",
  sourceType: "telegram",
  channelId: "1948320571",
  title: "Crypto Alpha Signals",
  handle: "@cryptoalphasignals",
  isPrivate: false,
  subscriberCount: 48_210,
  estimatedMessageCount: 152_842,
  capturedCount: 152_842,
  capturedThroughMessageId: "2101163413",
  status: "complete",
}

function renderReader(onBack = vi.fn()) {
  render(<ReaderPage chat={completeChat} onBack={onBack} />)
  return onBack
}

function entries() {
  return screen.getAllByRole("article", { name: /source message/i })
}

describe("source labeling reader", () => {
  it("shows Telegram as the only V1 source with no future source menu", () => {
    renderReader()

    expect(screen.getByText("Telegram")).toBeVisible()
    expect(screen.queryByText("Discord")).not.toBeInTheDocument()
    expect(screen.queryByText("X.com")).not.toBeInTheDocument()
    expect(screen.queryByText("API / Webhook")).not.toBeInTheDocument()
  })

  it("opens the labeling reader for the chat it was given", () => {
    renderReader()

    expect(
      screen.getByRole("heading", { name: /crypto alpha signals/i }),
    ).toBeVisible()
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toHaveTextContent(
      "Crypto Alpha Signals",
    )
  })

  it("returns to the sources list from the breadcrumb", async () => {
    const user = userEvent.setup()
    const onBack = renderReader()

    await user.click(screen.getByRole("button", { name: /sources/i }))

    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it("offers only Signal and Non-signal label actions", () => {
    renderReader()

    const firstEntry = entries()[0]

    expect(within(firstEntry).getByRole("button", { name: "Mark as Signal" })).toBeVisible()
    expect(
      within(firstEntry).getByRole("button", { name: "Mark as Non-signal" }),
    ).toBeVisible()
    expect(screen.queryByRole("button", { name: /noise/i })).not.toBeInTheDocument()
  })

  it("keeps each entry's Signal action before its Non-signal action", () => {
    renderReader()

    const actions = within(entries()[0]).getByLabelText("Label actions")
    const buttons = within(actions).getAllByRole("button")

    expect(buttons[0]).toHaveAccessibleName("Mark as Signal")
    expect(buttons[1]).toHaveAccessibleName("Mark as Non-signal")
  })

  it("renders realistic multiline Telegram signal messages", () => {
    renderReader()

    const stream = screen.getByLabelText("Messages")

    expect(stream).toHaveTextContent("МОНЕТА: #ENA/USDT")
    expect(stream).toHaveTextContent("ПОКУПКА: SHORT")
    expect(stream).toHaveTextContent("ПЛЕЧО: 16x")
    expect(stream).toHaveTextContent("Вход: 0.09109$")
    expect(stream).toHaveTextContent("Стоп: 0.09925$")
  })

  it("accents trade symbols as their own mono tokens", () => {
    renderReader()

    const symbol = screen.getAllByText("#ENA/USDT")[0]

    expect(symbol).toHaveClass("tok-symbol")
  })

  it("highlights the first visible message by default", () => {
    renderReader()

    expect(entries()[0]).toHaveAttribute("aria-current", "true")
  })

  it("keeps search as the first message control", () => {
    renderReader()

    const controls = screen.getByLabelText("Message controls")
    const firstControl = controls.firstElementChild

    expect(firstControl).toHaveAccessibleName("Search messages")
  })

  it("marks a labeled signal entry with the signal state", async () => {
    const user = userEvent.setup()
    renderReader()

    await selectMessageFilter("All")

    const firstEntry = entries()[0]
    await user.click(
      within(firstEntry).getByRole("button", { name: "Mark as Signal" }),
    )

    expect(firstEntry).toHaveClass("entry-signal")
  })

  it("marks a labeled non-signal entry with the non-signal state", async () => {
    const user = userEvent.setup()
    renderReader()

    await selectMessageFilter("All")

    const firstEntry = entries()[0]
    await user.click(
      within(firstEntry).getByRole("button", { name: "Mark as Non-signal" }),
    )

    expect(firstEntry).toHaveClass("entry-non_signal")
  })

  it("keeps the filter options open long enough to select one", async () => {
    renderReader()

    await selectMessageFilter("All")

    expect(screen.getByRole("button", { name: "Message filter: All" })).toBeVisible()
    expect(screen.queryByRole("listbox", { name: "Message filter options" })).not.toBeInTheDocument()
  })

  it("labels the highlighted message with cross-platform keyboard shortcuts", async () => {
    const user = userEvent.setup()
    renderReader()

    const firstMessageId = entries()[0].textContent

    await user.keyboard("s")

    expect(within(screen.getByLabelText("Label stats")).getByText("25")).toBeVisible()
    expect(entries()[0].textContent).not.toBe(firstMessageId)

    await user.keyboard("n")

    expect(within(screen.getByLabelText("Label stats")).getByText("26")).toBeVisible()
  })

  it("moves the highlighted message with keyboard navigation", async () => {
    const user = userEvent.setup()
    renderReader()

    const rows = entries()

    await user.keyboard("{ArrowDown}")

    expect(rows[0]).toHaveAttribute("aria-current", "false")
    expect(rows[1]).toHaveAttribute("aria-current", "true")

    await user.keyboard("k")

    expect(rows[0]).toHaveAttribute("aria-current", "true")
    expect(rows[1]).toHaveAttribute("aria-current", "false")
  })

  it("does not label while typing in search", async () => {
    const user = userEvent.setup()
    renderReader()

    await user.click(screen.getByRole("searchbox", { name: "Search messages" }))
    await user.keyboard("s")

    expect(within(screen.getByLabelText("Label stats")).getByText("24")).toBeVisible()
  })

  it("counts labeled messages in the stats header", async () => {
    const user = userEvent.setup()
    renderReader()

    const stats = screen.getByLabelText("Label stats")
    expect(within(stats).getByText("24")).toBeVisible()

    const firstUnlabeled = entries().find((entry) =>
      within(entry).queryByText("Unlabeled"),
    )
    expect(firstUnlabeled).toBeDefined()

    await user.click(
      within(firstUnlabeled as HTMLElement).getByRole("button", {
        name: "Mark as Signal",
      }),
    )

    expect(within(stats).getByText("25")).toBeVisible()
  })

  it("filters to unlabeled messages and keeps pagination compact", async () => {
    renderReader()

    await selectMessageFilter("Unlabeled")

    expect(screen.getByText(/100 per page/i)).toBeVisible()
    expect(screen.getAllByText("Unlabeled").length).toBeGreaterThan(1)
  })
})

async function selectMessageFilter(label: string) {
  const user = userEvent.setup()

  await user.click(screen.getByRole("button", { name: /message filter:/i }))
  expect(screen.getByRole("listbox", { name: "Message filter options" })).toBeVisible()
  await user.click(screen.getByRole("option", { name: label }))
}
