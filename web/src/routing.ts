export type Route =
  | { view: "sources" }
  | { view: "reader"; chatId: string }

const SOURCES_HASH = "#/sources"

export function parseRoute(hash: string): Route {
  const segments = stripHashPrefix(hash).split("/").filter(Boolean)

  if (segments[0] === "reader" && segments[1]) {
    return { view: "reader", chatId: decodeURIComponent(segments[1]) }
  }

  return { view: "sources" }
}

export function sourcesHash(): string {
  return SOURCES_HASH
}

export function readerHash(chatId: string): string {
  return `#/reader/${encodeURIComponent(chatId)}`
}

function stripHashPrefix(hash: string): string {
  return hash.replace(/^#/, "").replace(/^\//, "")
}
