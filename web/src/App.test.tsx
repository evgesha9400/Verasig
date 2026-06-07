import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import App from "./App"

describe("source labeling reader", () => {
  it("uses a dark-primary review surface", () => {
    const { container } = render(<App />)

    expect(container.querySelector(".app-shell")).toHaveAttribute(
      "data-theme",
      "dark-primary",
    )
  })

  it("shows only Telegram as the V1 source and no future source menu", () => {
    render(<App />)

    expect(screen.getByRole("combobox", { name: "Source type" })).toHaveValue(
      "telegram",
    )
    expect(screen.queryByText("Discord")).not.toBeInTheDocument()
    expect(screen.queryByText("X.com")).not.toBeInTheDocument()
    expect(screen.queryByText("API / Webhook")).not.toBeInTheDocument()
  })

  it("offers only Signal and Non-signal label actions", () => {
    render(<App />)

    const firstMessage = screen.getAllByRole("row", { name: /source message/i })[0]

    expect(within(firstMessage).getByRole("button", { name: "Mark as Signal" })).toBeVisible()
    expect(
      within(firstMessage).getByRole("button", { name: "Mark as Non-signal" }),
    ).toBeVisible()
    expect(screen.queryByRole("button", { name: /noise/i })).not.toBeInTheDocument()
  })

  it("renders realistic multiline Telegram signal messages", () => {
    render(<App />)

    expect(screen.getAllByText(/МОНЕТА: #ENA\/USDT/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/ПОКУПКА: SHORT/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/ПЛЕЧО: 16x/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Вход: 0\.09109\$/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Стоп: 0\.09925\$/i).length).toBeGreaterThan(0)
  })

  it("highlights the first visible message by default", () => {
    render(<App />)

    expect(screen.getAllByRole("row", { name: /source message/i })[0]).toHaveAttribute(
      "aria-current",
      "true",
    )
  })

  it("orders scan columns for fast labeling", () => {
    render(<App />)

    const header = screen.getByRole("row", {
      name: /source msg id posted captured type message buttons/i,
    })

    expect(header).toHaveTextContent(
      "Source msg idPostedCapturedTypeMessageButtons",
    )
  })

  it("keeps label buttons immediately after the message column", () => {
    render(<App />)

    const firstMessage = screen.getAllByRole("row", { name: /source message/i })[0]
    const rowCells = Array.from(firstMessage.children)
    const messageCell = rowCells.at(4)
    const buttonCell = rowCells.at(5)

    expect(messageCell).toHaveAccessibleName("Message")
    expect(buttonCell).toHaveAccessibleName("Label actions")
    expect(within(buttonCell as HTMLElement).getByRole("button", { name: "Mark as Signal" })).toBeVisible()
    expect(
      within(buttonCell as HTMLElement).getByRole("button", { name: "Mark as Non-signal" }),
    ).toBeVisible()
  })

  it("colors a labeled signal row with the signal row state", async () => {
    const user = userEvent.setup()
    render(<App />)

    await selectMessageFilter("All")

    const firstMessage = screen.getAllByRole("row", { name: /source message/i })[0]

    await user.click(
      within(firstMessage).getByRole("button", { name: "Mark as Signal" }),
    )

    expect(firstMessage).toHaveClass("message-row-signal")
  })

  it("colors a labeled non-signal row with the non-signal row state", async () => {
    const user = userEvent.setup()
    render(<App />)

    await selectMessageFilter("All")

    const firstMessage = screen.getAllByRole("row", { name: /source message/i })[0]

    await user.click(
      within(firstMessage).getByRole("button", { name: "Mark as Non-signal" }),
    )

    expect(firstMessage).toHaveClass("message-row-non_signal")
  })

  it("keeps search as the first message control", () => {
    render(<App />)

    const controls = screen.getByLabelText("Message controls")
    const firstControl = controls.firstElementChild

    expect(firstControl).toHaveAccessibleName("Search messages")
  })

  it("keeps the filter options open long enough to select one", async () => {
    render(<App />)

    await selectMessageFilter("All")

    expect(screen.getByRole("button", { name: "Message filter: All" })).toBeVisible()
    expect(screen.queryByRole("listbox", { name: "Message filter options" })).not.toBeInTheDocument()
  })

  it("labels the highlighted message with cross-platform keyboard shortcuts", async () => {
    const user = userEvent.setup()
    render(<App />)

    const firstMessageId = screen
      .getAllByRole("row", { name: /source message/i })[0]
      .textContent

    await user.keyboard("s")

    expect(within(screen.getByLabelText("Label stats")).getByText("25")).toBeVisible()
    expect(screen.getAllByRole("row", { name: /source message/i })[0].textContent).not.toBe(
      firstMessageId,
    )

    await user.keyboard("n")

    expect(within(screen.getByLabelText("Label stats")).getByText("26")).toBeVisible()
  })

  it("moves the highlighted message with keyboard navigation", async () => {
    const user = userEvent.setup()
    render(<App />)

    const rows = screen.getAllByRole("row", { name: /source message/i })

    await user.keyboard("{ArrowDown}")

    expect(rows[0]).toHaveAttribute("aria-current", "false")
    expect(rows[1]).toHaveAttribute("aria-current", "true")

    await user.keyboard("k")

    expect(rows[0]).toHaveAttribute("aria-current", "true")
    expect(rows[1]).toHaveAttribute("aria-current", "false")
  })

  it("does not label while typing in search", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("searchbox", { name: "Search messages" }))
    await user.keyboard("s")

    expect(within(screen.getByLabelText("Label stats")).getByText("24")).toBeVisible()
  })

  it("updates stats when a message is labeled", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByText("Labeled")).toBeVisible()
    expect(screen.getByText("24")).toBeVisible()

    const firstUnlabeledRow = screen
      .getAllByRole("row", { name: /source message/i })
      .find((row) => within(row).queryByText("Unlabeled"))

    expect(firstUnlabeledRow).toBeDefined()

    await user.click(
      within(firstUnlabeledRow as HTMLElement).getByRole("button", {
        name: "Mark as Signal",
      }),
    )

    expect(screen.getByText("25")).toBeVisible()
  })

  it("filters to unlabeled messages and keeps pagination compact", async () => {
    render(<App />)

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
