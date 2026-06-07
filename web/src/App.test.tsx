import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"

beforeEach(() => {
  window.location.hash = ""
})

afterEach(() => {
  vi.useRealTimers()
})

describe("app shell and routing", () => {
  it("uses a dark-primary review surface", () => {
    const { container } = render(<App />)

    expect(container.querySelector(".app-shell")).toHaveAttribute(
      "data-theme",
      "dark-primary",
    )
  })

  it("lands on the Telegram chats page by default", async () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "Telegram chats" })).toBeVisible()
    expect(await screen.findByText("Crypto Alpha Signals")).toBeVisible()
  })

  it("opens the reader for a backfilled chat from its hash route", () => {
    window.location.hash = "#/reader/chat_crypto_alpha"
    render(<App />)

    expect(screen.getByLabelText("Source labeling reader")).toBeInTheDocument()
    expect(
      screen.queryByRole("heading", { name: "Telegram chats" }),
    ).not.toBeInTheDocument()
  })

  it("redirects to sources when the requested chat is not backfilled", async () => {
    window.location.hash = "#/reader/chat_matematik"
    render(<App />)

    expect(screen.queryByLabelText("Source labeling reader")).not.toBeInTheDocument()
    await waitFor(() => expect(window.location.hash).toBe("#/sources"))
    expect(screen.getByRole("heading", { name: "Telegram chats" })).toBeVisible()
  })

  it("returns from the reader to the chats list via the breadcrumb", async () => {
    const user = userEvent.setup()
    window.location.hash = "#/reader/chat_crypto_alpha"
    render(<App />)

    await user.click(screen.getByRole("button", { name: /sources/i }))

    expect(
      await screen.findByRole("heading", { name: "Telegram chats" }),
    ).toBeVisible()
    expect(screen.queryByLabelText("Source labeling reader")).not.toBeInTheDocument()
  })

  it("blocks every other backfill once one is running", () => {
    vi.useFakeTimers()
    render(<App />)
    act(() => {
      vi.advanceTimersByTime(700)
    })

    act(() => {
      fireEvent.click(screen.getAllByRole("button", { name: "Start backfill" })[0])
    })

    const remainingStarts = screen.getAllByRole("button", { name: "Start backfill" })
    expect(remainingStarts.length).toBeGreaterThan(0)
    remainingStarts.forEach((button) => expect(button).toBeDisabled())
  })

  it("advances a running backfill to completion and exposes its reader", () => {
    vi.useFakeTimers()
    render(<App />)
    act(() => {
      vi.advanceTimersByTime(700)
    })

    const openLinksBefore = screen.getAllByRole("link", { name: /open reader/i }).length

    act(() => {
      fireEvent.click(screen.getAllByRole("button", { name: "Start backfill" })[0])
    })
    act(() => {
      vi.advanceTimersByTime(12_000)
    })

    expect(
      screen.getAllByRole("link", { name: /open reader/i }).length,
    ).toBe(openLinksBefore + 1)
  })
})
