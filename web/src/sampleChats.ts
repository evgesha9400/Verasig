import type { SourceChat } from "./sourceChats"

type ChatSeed = {
  id: string
  channelId: string
  title: string
  handle: string | null
  subscriberCount: number
  estimatedMessageCount: number
  capturedCount: number
  status: SourceChat["status"]
  failureReason?: string
}

const chatSeeds: ChatSeed[] = [
  {
    id: "chat_crypto_alpha",
    channelId: "1948320571",
    title: "Crypto Alpha Signals",
    handle: "@cryptoalphasignals",
    subscriberCount: 48_210,
    estimatedMessageCount: 152_842,
    capturedCount: 152_842,
    status: "complete",
  },
  {
    id: "chat_altcoin_daily",
    channelId: "1772044190",
    title: "Altcoin Daily Calls",
    handle: "@altcoindailycalls",
    subscriberCount: 64_500,
    estimatedMessageCount: 89_430,
    capturedCount: 89_430,
    status: "complete",
  },
  {
    id: "chat_matematik",
    channelId: "1620994815",
    title: "Математик Торговля",
    handle: null,
    subscriberCount: 12_140,
    estimatedMessageCount: 48_320,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_whale_pump",
    channelId: "1503887642",
    title: "Whale Pump Alerts",
    handle: "@whalepumpalerts",
    subscriberCount: 91_030,
    estimatedMessageCount: 153_000,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_scalp_room",
    channelId: "1399201774",
    title: "Scalp Room — Inner Circle",
    handle: null,
    subscriberCount: 3_280,
    estimatedMessageCount: 48_300,
    capturedCount: 31_204,
    status: "idle",
  },
  {
    id: "chat_defi_degens",
    channelId: "1844720913",
    title: "DeFi Degens",
    handle: "@defidegens",
    subscriberCount: 7_420,
    estimatedMessageCount: 26_140,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_futures_sniper",
    channelId: "1655093320",
    title: "Futures Sniper",
    handle: "@futuressniper",
    subscriberCount: 27_860,
    estimatedMessageCount: 61_770,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_blackbox_vip",
    channelId: "1290748653",
    title: "BlackBox VIP",
    handle: null,
    subscriberCount: 1_940,
    estimatedMessageCount: 19_880,
    capturedCount: 4_120,
    status: "failed",
    failureReason: "Flood-wait limit reached at message 4,120",
  },
  {
    id: "chat_spot_swings",
    channelId: "1733650298",
    title: "Spot Swings",
    handle: "@spotswings",
    subscriberCount: 15_640,
    estimatedMessageCount: 34_900,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_liquidation_hunter",
    channelId: "1588021947",
    title: "Liquidation Hunter",
    handle: "@liquidationhunter",
    subscriberCount: 8_820,
    estimatedMessageCount: 42_010,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_macro_desk",
    channelId: "1467722530",
    title: "Macro Desk",
    handle: "@macrodesk",
    subscriberCount: 42_050,
    estimatedMessageCount: 21_460,
    capturedCount: 0,
    status: "idle",
  },
  {
    id: "chat_perehvat",
    channelId: "1391884027",
    title: "Перехват Сигналов",
    handle: null,
    subscriberCount: 5_110,
    estimatedMessageCount: 57_300,
    capturedCount: 0,
    status: "idle",
  },
]

export function makeSampleChats(): SourceChat[] {
  return chatSeeds.map(toSourceChat)
}

function toSourceChat(seed: ChatSeed): SourceChat {
  return {
    id: seed.id,
    sourceType: "telegram",
    channelId: seed.channelId,
    title: seed.title,
    handle: seed.handle,
    isPrivate: seed.handle === null,
    subscriberCount: seed.subscriberCount,
    estimatedMessageCount: seed.estimatedMessageCount,
    capturedCount: seed.capturedCount,
    capturedThroughMessageId: capturedThroughId(seed),
    status: seed.status,
    ...(seed.failureReason ? { failureReason: seed.failureReason } : {}),
  }
}

function capturedThroughId(seed: ChatSeed): string | null {
  if (seed.capturedCount === 0) {
    return null
  }

  return String(Number(seed.channelId) + seed.capturedCount)
}
