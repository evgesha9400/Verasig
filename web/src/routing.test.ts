import { describe, expect, it } from "vitest"
import { parseRoute, readerHash, sourcesHash } from "./routing"

describe("hash routing", () => {
  it("treats an empty or root hash as the sources view", () => {
    expect(parseRoute("")).toEqual({ view: "sources" })
    expect(parseRoute("#")).toEqual({ view: "sources" })
    expect(parseRoute("#/")).toEqual({ view: "sources" })
    expect(parseRoute("#/sources")).toEqual({ view: "sources" })
  })

  it("parses a reader route with its chat id", () => {
    expect(parseRoute("#/reader/chat_01")).toEqual({
      view: "reader",
      chatId: "chat_01",
    })
  })

  it("falls back to sources for an unknown or incomplete route", () => {
    expect(parseRoute("#/distillation")).toEqual({ view: "sources" })
    expect(parseRoute("#/reader/")).toEqual({ view: "sources" })
  })

  it("builds hashes that round-trip through the parser", () => {
    expect(parseRoute(sourcesHash())).toEqual({ view: "sources" })
    expect(parseRoute(readerHash("chat_42"))).toEqual({
      view: "reader",
      chatId: "chat_42",
    })
  })

  it("escapes chat ids that contain url-significant characters", () => {
    expect(parseRoute(readerHash("chat/with space"))).toEqual({
      view: "reader",
      chatId: "chat/with space",
    })
  })
})
