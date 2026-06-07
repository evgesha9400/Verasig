import { describe, expect, it } from "vitest"
import { tokenizeMessage } from "./messageMarkup"

describe("message markup tokenizer", () => {
  it("preserves the original text exactly, including newlines", () => {
    const text = "#ETH/USDT SHORT\n\nEntry: 3,514-3,529\nStop: 3,612"

    const rebuilt = tokenizeMessage(text)
      .map((token) => token.value)
      .join("")

    expect(rebuilt).toBe(text)
  })

  it("tags symbols, sides, and numbers", () => {
    const tokens = tokenizeMessage("#ETH/USDT SHORT entry 3,514 leverage 12x")

    expect(tokens).toContainEqual({ type: "symbol", value: "#ETH/USDT" })
    expect(tokens).toContainEqual({ type: "side", value: "SHORT" })
    expect(tokens).toContainEqual({ type: "number", value: "3,514" })
    expect(tokens).toContainEqual({ type: "number", value: "12x" })
  })

  it("leaves prose without trade fields as a single text token", () => {
    const tokens = tokenizeMessage("Wait for confirmation candle before entering.")

    expect(tokens).toEqual([
      { type: "text", value: "Wait for confirmation candle before entering." },
    ])
  })

  it("matches sides case-insensitively and only as whole words", () => {
    const tokens = tokenizeMessage("going long here, not shorting")

    expect(tokens.some((token) => token.type === "side" && token.value === "long")).toBe(
      true,
    )
    expect(tokens.some((token) => token.type === "side")).toBe(true)
    expect(tokens.find((token) => token.value === "shorting")).toBeUndefined()
  })
})
