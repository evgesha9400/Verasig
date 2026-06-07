export type MessageTokenType = "text" | "symbol" | "side" | "number"

export type MessageToken = {
  type: MessageTokenType
  value: string
}

const TOKEN_PATTERN =
  /(#[A-Za-z0-9]+(?:\/[A-Za-z0-9]+)?)|(\b(?:LONG|SHORT)\b)|(\d[\d.,]*(?:\$|x)?)/gi

export function tokenizeMessage(text: string): MessageToken[] {
  const tokens: MessageToken[] = []
  let cursor = 0

  for (const match of text.matchAll(TOKEN_PATTERN)) {
    const start = match.index ?? 0
    pushText(tokens, text.slice(cursor, start))
    tokens.push(classifyMatch(match))
    cursor = start + match[0].length
  }

  pushText(tokens, text.slice(cursor))
  return tokens
}

function pushText(tokens: MessageToken[], value: string): void {
  if (value.length > 0) {
    tokens.push({ type: "text", value })
  }
}

function classifyMatch(match: RegExpMatchArray): MessageToken {
  if (match[1]) {
    return { type: "symbol", value: match[1] }
  }

  if (match[2]) {
    return { type: "side", value: match[2] }
  }

  return { type: "number", value: match[0] }
}
