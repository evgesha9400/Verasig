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
    const user = userEvent.setup()
    render(<App />)

    await user.selectOptions(screen.getByRole("combobox", { name: "Message filter" }), [
      "unlabeled",
    ])

    expect(screen.getByText(/100 per page/i)).toBeVisible()
    expect(screen.getAllByText("Unlabeled").length).toBeGreaterThan(1)
  })
})
