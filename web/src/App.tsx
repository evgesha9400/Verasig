import { CheckCircle2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import "./App.css"
import ChatsPage from "./ChatsPage"
import ReaderPage from "./ReaderPage"
import { makeSampleChats } from "./sampleChats"
import { parseRoute, sourcesHash, type Route } from "./routing"
import {
  advanceBackfill,
  cancelBackfill,
  estimateSecondsRemaining,
  filterChats,
  findChatById,
  findRunningChat,
  isBackfilled,
  startBackfill,
  summarizeChats,
} from "./sourceChats"

const CHAT_LOAD_MS = 650
const BACKFILL_TICK_MS = 200
const BACKFILL_TICKS_TO_COMPLETE = 48

function App() {
  const route = useHashRoute()
  const [chats, setChats] = useState(makeSampleChats)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")

  const runningChat = findRunningChat(chats)
  const runningChatId = runningChat?.id

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), CHAT_LOAD_MS)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (!runningChatId) {
      return
    }

    const timer = setInterval(() => {
      setChats((current) =>
        advanceBackfill(current, runningChatId, capturePerTick(current, runningChatId)),
      )
    }, BACKFILL_TICK_MS)

    return () => clearInterval(timer)
  }, [runningChatId])

  function startChatBackfill(chatId: string) {
    setChats((current) => startBackfill(current, chatId))
  }

  function cancelChatBackfill(chatId: string) {
    setChats((current) => cancelBackfill(current, chatId))
  }

  const visibleChats = useMemo(
    () => filterChats(chats, searchQuery),
    [chats, searchQuery],
  )
  const summary = useMemo(() => summarizeChats(chats), [chats])
  const secondsRemaining = runningChat
    ? estimateSecondsRemaining(runningChat, capturesPerSecond(runningChat))
    : 0

  const readerChat = resolveReaderChat(route, chats)
  useRedirectWhenReaderUnavailable(route, readerChat)

  return (
    <main className="app-shell" data-theme="dark-primary">
      <AppBar />
      {readerChat ? (
        <ReaderPage chat={readerChat} onBack={navigateToSources} />
      ) : (
        <ChatsPage
          loading={loading}
          runningChat={runningChat}
          searchQuery={searchQuery}
          secondsRemaining={secondsRemaining}
          summary={summary}
          totalChats={chats.length}
          visibleChats={visibleChats}
          onCancelBackfill={cancelChatBackfill}
          onSearchChange={setSearchQuery}
          onStartBackfill={startChatBackfill}
        />
      )}
    </main>
  )
}

function AppBar() {
  return (
    <header className="app-bar">
      <a className="brand" href={sourcesHash()} aria-label="Verasig home">
        <span className="brand-mark" aria-hidden="true">
          <CheckCircle2 size={18} strokeWidth={2.4} />
        </span>
        <span>Verasig</span>
      </a>
      <nav className="app-nav" aria-label="Primary">
        <a aria-current="page" href={sourcesHash()}>
          Sources
        </a>
        <a href="#distillation">Distillation</a>
      </nav>
      <div className="account-chip" aria-label="Signed in account">
        EV
      </div>
    </header>
  )
}

function useHashRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(readHash()))

  useEffect(() => {
    function syncRoute() {
      setRoute(parseRoute(readHash()))
    }

    window.addEventListener("hashchange", syncRoute)
    return () => window.removeEventListener("hashchange", syncRoute)
  }, [])

  return route
}

function useRedirectWhenReaderUnavailable(
  route: Route,
  readerChat: ReturnType<typeof resolveReaderChat>,
) {
  useEffect(() => {
    if (route.view === "reader" && !readerChat) {
      navigateToSources()
    }
  }, [route, readerChat])
}

function resolveReaderChat(route: Route, chats: ReturnType<typeof makeSampleChats>) {
  if (route.view !== "reader") {
    return undefined
  }

  const chat = findChatById(chats, route.chatId)
  if (!chat || !isBackfilled(chat)) {
    return undefined
  }

  return chat
}

function navigateToSources() {
  window.location.hash = sourcesHash()
}

function capturePerTick(
  chats: ReturnType<typeof makeSampleChats>,
  chatId: string,
): number {
  const chat = findChatById(chats, chatId)
  if (!chat) {
    return 0
  }

  return Math.max(1, Math.ceil(chat.estimatedMessageCount / BACKFILL_TICKS_TO_COMPLETE))
}

function capturesPerSecond(chat: ReturnType<typeof makeSampleChats>[number]): number {
  const perTick = Math.max(
    1,
    Math.ceil(chat.estimatedMessageCount / BACKFILL_TICKS_TO_COMPLETE),
  )

  return perTick * (1000 / BACKFILL_TICK_MS)
}

function readHash(): string {
  return window.location.hash
}

export default App
