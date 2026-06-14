/* Verasig prototype — sample data */

/* ---- Chats retrieved from Telegram ---- */
export const CHATS = [
  {
    id: 'apex',
    name: 'Apex Crypto Calls',
    tag: '@apexcryptocalls',
    subscribers: 48230,
    tint: 'var(--viz-2)',
    initials: 'AC',
    status: 'new', // new | backfilling | failed | cancelled | backfilled | analyzed
    fetched: 0,
    lastDate: null,
    score: null
  },
  {
    id: 'whale',
    name: 'WhaleRoom VIP',
    tag: '@whaleroomvip',
    subscribers: 21984,
    tint: 'var(--viz-3)',
    initials: 'WR',
    status: 'analyzed',
    fetched: 9840,
    lastDate: 'Jun 6, 2026',
    score: 79,
    winRate: 58.6,
    pnl: 28.4,
    hasRisk: true,
    historyGaps: true // suspected — id-sequence gaps found on backfill
  },
  {
    id: 'delta',
    name: 'Delta Futures Signals',
    tag: '@deltafutures',
    subscribers: 73510,
    tint: 'var(--viz-5)',
    initials: 'DF',
    status: 'analyzed', // pre-analyzed example with a score
    fetched: 18420,
    lastDate: 'Jun 7, 2026',
    score: 86,
    winRate: 64.2,
    pnl: 41.8,
    hasRisk: true,
    signalDeletion: true // confirmed — re-backfill found extracted signals deleted; score floors to 0
  },
  {
    id: 'moon',
    name: 'MoonShot Alerts',
    tag: '@moonshotalerts',
    subscribers: 9120,
    tint: 'var(--viz-4)',
    initials: 'MS',
    status: 'cancelled', // partially backfilled, can retry
    fetched: 6240,
    lastDate: 'May 29, 2026',
    score: null
  },
  {
    id: 'quant',
    name: 'QuantEdge Research',
    tag: '@quantedge',
    subscribers: 33870,
    tint: 'var(--viz-6)',
    initials: 'QE',
    status: 'new',
    fetched: 0,
    lastDate: null,
    score: null
  }
]

/* ---- Messages for the Label/Verify loop. kind: signal | noise ----
   `truth` is the "correct" label, used to drive Verify outcomes. */
export const MESSAGES = [
  {
    id: 'm1',
    truth: 'signal',
    time: '08:42',
    date: 'Jun 6',
    author: 'Apex',
    text: 'LONG  BTC/USDT\nEntry  64,200 – 63,750\nStop   62,400\nTargets  66.5k / 68.2k / 71.0k\nLeverage  5–10x',
    media: null
  },
  {
    id: 'm2',
    truth: 'noise',
    time: '09:03',
    date: 'Jun 6',
    author: 'Apex',
    text: 'gm everyone. choppy open, BTC ranging under resistance. patience pays — no FOMO entries here.',
    media: null
  },
  {
    id: 'm3',
    truth: 'signal',
    time: '09:48',
    date: 'Jun 6',
    author: 'Apex',
    text: 'SHORT  ETH/USDT\nEntry  3,420\nSL  3,512\nTP  3,280 / 3,140 / 2,990',
    media: 'chart'
  },
  {
    id: 'm4',
    truth: 'noise',
    time: '10:15',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Join our VIP tier for premium leveraged calls and 1:1 mentoring. Link pinned above.',
    media: null
  },
  {
    id: 'm5',
    truth: 'signal',
    time: '11:02',
    date: 'Jun 6',
    author: 'Apex',
    text: 'SCALP  ARB/USDT long 1.124\nTight stop 1.092\nTarget 1.190\nClose half at 1.16',
    media: null
  },
  {
    id: 'm6',
    truth: 'noise',
    time: '11:30',
    date: 'Jun 6',
    author: 'Apex',
    text: 'BTC dominance ticking up again, alts bleeding on the lower timeframes. stay nimble.',
    media: null
  },
  {
    id: 'm7',
    truth: 'modifier',
    time: '12:14',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Move BTC stop to entry (break-even). First target 66.5k tagged — risk-free from here.',
    media: null,
    replyTo: {
      author: 'Apex',
      text: 'LONG BTC/USDT · Entry 64,200 – 63,750 · SL 62,400'
    },
    mod: {
      label: 'Move stop → break-even',
      via: 'reply',
      target: 'LONG BTC/USDT — Jun 6 · 08:42'
    }
  },
  {
    id: 'm8',
    truth: 'noise',
    time: '12:41',
    date: 'Jun 6',
    author: 'Apex',
    text: 'What are we thinking about the rate decision on Wednesday? drop your bias below 👇',
    media: null
  },
  {
    id: 'm9',
    truth: 'signal',
    time: '13:20',
    date: 'Jun 6',
    author: 'Apex',
    text: 'LONG  SOL/USDT\nEntry  148.5 – 146.0\nSL  141.8\nTP  158 / 165 / 178\nRisk 2% of book',
    media: 'chart'
  },
  {
    id: 'm10',
    truth: 'noise',
    time: '13:55',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Welcome to all 200 new members this week! Read the pinned rules before posting. 🙌',
    media: null
  },
  {
    id: 'm11',
    truth: 'signal',
    time: '14:30',
    date: 'Jun 6',
    author: 'Apex',
    text: 'SHORT  DOGE/USDT 0.1620\nSL 0.1685\nTP 0.1540 / 0.1480',
    media: null
  },
  {
    id: 'm12',
    truth: 'noise',
    time: '15:02',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Markets closed green. Recap thread + this week’s scorecard dropping tonight.',
    media: 'image'
  },
  {
    id: 'm13',
    truth: 'signal',
    time: '15:48',
    date: 'Jun 6',
    author: 'Apex',
    text: 'LONG  LINK/USDT\nEntry 18.40\nSL 17.60\nTP 19.8 / 21.2 / 23.0',
    media: null
  },
  {
    id: 'm14',
    truth: 'noise',
    time: '16:20',
    date: 'Jun 6',
    author: 'Apex',
    text: 'reminder: never risk more than you can afford. position sizing > everything.',
    media: null
  },
  {
    id: 'm15',
    truth: 'modifier',
    time: '17:05',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Close ARB at TP2 1.19 — full position out. +5.9% on the scalp. clean.',
    media: null,
    replyTo: { author: 'Apex', text: 'SCALP ARB/USDT long 1.124 · Tight stop 1.092' },
    mod: {
      label: 'Close (full)',
      via: 'reply',
      target: 'SCALP ARB/USDT — Jun 6 · 11:02'
    }
  },
  {
    id: 'm16',
    truth: 'modifier',
    time: '17:40',
    date: 'Jun 6',
    author: 'Apex',
    text: 'BTC dipping into demand — averaging down 2x at 62,800. Same invalidation, same targets.',
    media: null,
    replyTo: {
      author: 'Apex',
      text: 'LONG BTC/USDT · Entry 64,200 – 63,750 · SL 62,400'
    },
    mod: {
      label: 'Average down ×2',
      via: 'reply',
      target: 'LONG BTC/USDT — Jun 6 · 08:42'
    }
  },
  {
    id: 'm17',
    truth: 'noise',
    time: '18:01',
    date: 'Jun 6',
    author: 'Apex',
    text: 'Big week ahead — CPI Wednesday, FOMC minutes Thursday. Expect chop. Size accordingly.',
    media: null
  },
  {
    id: 'm18',
    truth: 'modifier',
    time: '18:26',
    date: 'Jun 6',
    author: 'Apex',
    text: 'out of SOL here +6%. solid day team ✅',
    media: null,
    mod: {
      label: 'Close (full)',
      via: 'inferred',
      target: 'LONG SOL/USDT — most recent open SOL position'
    }
  }
]

/* ---- AI-distilled rules ---- */
export const DISTILLED_RULES = [
  {
    id: 'r1',
    label: 'Has a directional verb',
    detail: 'Matches LONG / SHORT / SCALP / CLOSE near a ticker',
    match: 0.94
  },
  {
    id: 'r2',
    label: 'Contains a ticker pair',
    detail: 'e.g. BTC/USDT, ETH/USDT, SOL/USDT',
    match: 0.98
  },
  {
    id: 'r3',
    label: 'Defines entry + stop',
    detail: 'Explicit entry or "SL" / "stop" value present',
    match: 0.91
  },
  {
    id: 'r4',
    label: 'Has at least one target',
    detail: '"TP" / "Target" with a price level',
    match: 0.88
  },
  {
    id: 'r5',
    label: 'Links updates to their signal',
    detail: 'Reply-to → parent signal; else most recent open position in symbol',
    match: 0.92
  },
  {
    id: 'r6',
    label: 'Excludes promo & chatter',
    detail: 'Drops "VIP", "link in bio", greetings, recaps',
    match: 0.96
  }
]

/* ---- Verify pass: messages the AI auto-classified as Signal ---- */
export const VERIFY_SAMPLES = [
  {
    id: 'v1',
    truth: 'signal',
    text: 'LONG  AVAX/USDT\nEntry 34.20\nSL 32.80\nTP 37.5 / 40.0',
    media: null,
    predicted: 'signal'
  },
  {
    id: 'v2',
    truth: 'signal',
    text: 'SHORT  XRP/USDT 0.5240\nSL 0.5410\nTP 0.502 / 0.488',
    media: null,
    predicted: 'signal'
  },
  {
    id: 'v3',
    truth: 'noise',
    text: 'Scaling our SOL runner — chart looks textbook. who’s still holding? 📈',
    media: 'chart',
    predicted: 'signal'
  },
  {
    id: 'v4',
    truth: 'signal',
    text: 'LONG  OP/USDT\nEntry 2.18\nSL 2.04\nTP 2.42 / 2.65',
    media: null,
    predicted: 'signal'
  },
  {
    id: 'v5',
    truth: 'signal',
    text: 'CLOSE  ETH short at 3,140 — TP2 tagged. +8.1% banked.',
    media: null,
    predicted: 'signal'
  },
  {
    id: 'v6',
    truth: 'signal',
    text: 'SCALP  INJ/USDT long 24.10\nStop 23.40\nTarget 25.8',
    media: null,
    predicted: 'signal'
  }
]

/* ---- Exchanges ---- */
export const EXCHANGES = [
  {
    id: 'bybit',
    name: 'Bybit',
    tint: 'var(--viz-4)',
    brand: '#F7A600',
    initials: 'BY',
    status: 'available',
    kind: 'Derivatives · Spot',
    connected: false,
    account: 'J7n2…wL · trade-only'
  }
]

/* ---- Signals — extracted output of analyzed feeds, shown on the Signals page.
   Each ties back to a feedId (the Telegram chat) and its source.
   status: 'tested'    = backtested (defines a stop-loss + at least one target);
                         carries an `outcome` ('profit' | 'loss') + `pnl` result
           'untested'  = extracted with risk management but still queued — not yet backtested
           'skipped'   = excluded from the backtest because it had no risk management
   deleted: true       = removed from the channel's history after extraction ---- */
export const SIGNALS = [
  // Delta Futures Signals (delta)
  {
    id: 'SIG-9F21',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'BTC/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+9.8%',
    date: 'Jun 7',
    time: '14:32',
    entry: '64,200',
    stop: '62,400',
    tp: '66.5k / 68.2k / 71.0k',
    deleted: true
  },
  {
    id: 'SIG-9E0C',
    feedId: 'delta',
    side: 'SHORT',
    symbol: 'ETH/USDT',
    status: 'tested',
    outcome: 'loss',
    pnl: '−4.2%',
    date: 'Jun 7',
    time: '13:08',
    entry: '3,420',
    stop: '3,512',
    tp: '3,280 / 3,140 / 2,990'
  },
  {
    id: 'SIG-9D77',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'SOL/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+9.7%',
    date: 'Jun 7',
    time: '11:20',
    entry: '148.5',
    stop: '141.8',
    tp: '158 / 165 / 178',
    mods: [
      {
        id: 'MOD-2241',
        kind: 'avg_down',
        date: 'Jun 7',
        time: '13:05',
        via: 'reply',
        price: '145.2',
        text: 'SOL retesting support — averaging down 2x at 145.2. Same stop, same targets. 🎯',
        effect: 'Avg entry 148.5 → 146.3 · size ×3'
      },
      {
        id: 'MOD-2256',
        kind: 'partial',
        date: 'Jun 7',
        time: '15:40',
        via: 'reply',
        price: '158.0',
        text: 'TP1 tagged at 158 — closing half here. Stops to entry on the rest.',
        effect: '50% out at +8.0%'
      },
      {
        id: 'MOD-2270',
        kind: 'close',
        date: 'Jun 7',
        time: '18:22',
        via: 'reply',
        price: '162.5',
        text: 'Closing the rest of SOL at 162.5. Great trade team ✅',
        effect: 'Remaining 50% out at +11.1%'
      }
    ],
    effective: {
      entry: '146.3',
      entryNote: 'avg of 2 fills',
      closedBy: 'author',
      pnl: '+9.7%',
      note: 'Backtest follows the author’s exits — raw targets alone would have shown +14.6%.'
    }
  },
  {
    id: 'SIG-9C40',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'ARB/USDT',
    status: 'skipped',
    date: 'Jun 7',
    time: '10:02',
    entry: '1.124',
    stop: null,
    tp: null,
    deleted: true
  },
  {
    id: 'SIG-9B18',
    feedId: 'delta',
    side: 'SHORT',
    symbol: 'DOGE/USDT',
    status: 'skipped',
    date: 'Jun 6',
    time: '16:44',
    entry: '0.1620',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-9A02',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'LINK/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+7.1%',
    date: 'Jun 6',
    time: '15:48',
    entry: '18.40',
    stop: '17.60',
    tp: '19.8 / 21.2 / 23.0',
    deleted: true
  },
  {
    id: 'SIG-98E5',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'AVAX/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+11.2%',
    date: 'Jun 6',
    time: '12:31',
    entry: '34.20',
    stop: '32.80',
    tp: '37.5 / 40.0'
  },
  {
    id: 'SIG-97A9',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'OP/USDT',
    status: 'tested',
    outcome: 'loss',
    pnl: '−5.6%',
    date: 'Jun 5',
    time: '17:12',
    entry: '2.18',
    stop: '2.04',
    tp: '2.42 / 2.65'
  },
  {
    id: 'SIG-9655',
    feedId: 'delta',
    side: 'SHORT',
    symbol: 'XRP/USDT',
    status: 'skipped',
    date: 'Jun 5',
    time: '09:55',
    entry: '0.5240',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-9510',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'INJ/USDT',
    status: 'untested',
    date: 'Jun 4',
    time: '08:18',
    entry: '24.10',
    stop: '23.40',
    tp: '25.8 / 27.4',
    mods: [
      {
        id: 'MOD-1984',
        kind: 'avg_up',
        date: 'Jun 4',
        time: '11:36',
        via: 'reply',
        price: '25.10',
        text: 'INJ breaking out — adding 1.5x at 25.10. Momentum is real.',
        effect: 'Avg entry 24.10 → 24.70 · size ×2.5'
      }
    ],
    effective: { entry: '24.70', entryNote: 'avg of 2 fills' }
  },
  {
    id: 'SIG-93B7',
    feedId: 'delta',
    side: 'LONG',
    symbol: 'NEAR/USDT',
    status: 'skipped',
    cancelled: true,
    date: 'Jun 3',
    time: '13:44',
    entry: '6.42',
    stop: '6.08',
    tp: '6.95 / 7.40',
    mods: [
      {
        id: 'MOD-1812',
        kind: 'cancel',
        date: 'Jun 3',
        time: '14:10',
        via: 'reply',
        text: 'Cancel the NEAR long — lost the level before fill. Stand down.',
        effect: 'Cancelled before entry — excluded from backtest'
      }
    ],
    effective: { cancelled: true }
  },

  // WhaleRoom VIP (whale)
  {
    id: 'SIG-8F33',
    feedId: 'whale',
    side: 'LONG',
    symbol: 'BTC/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+3.6%',
    date: 'Jun 7',
    time: '13:50',
    entry: '63,900',
    stop: '61,800',
    tp: '66.0k / 69.5k',
    mods: [
      {
        id: 'MOD-7702',
        kind: 'move_stop',
        date: 'Jun 7',
        time: '15:02',
        via: 'reply',
        price: '63,900',
        text: 'BTC printing higher lows — stop to break-even 63,900. Risk-free runner now.',
        effect: 'Stop 61,800 → 63,900 (break-even)'
      },
      {
        id: 'MOD-7719',
        kind: 'close',
        date: 'Jun 7',
        time: '19:48',
        via: 'reply',
        price: '66,200',
        text: 'Taking BTC off at 66,200 ahead of CPI. +3.6% banked 🔒',
        effect: 'Closed at +3.6%'
      }
    ],
    effective: {
      stop: '63,900',
      stopNote: 'moved to break-even',
      closedBy: 'author',
      pnl: '+3.6%',
      note: 'Author exited before TP1 — raw targets would have shown +8.4%.'
    }
  },
  {
    id: 'SIG-8E91',
    feedId: 'whale',
    side: 'SHORT',
    symbol: 'SUI/USDT',
    status: 'skipped',
    date: 'Jun 7',
    time: '11:41',
    entry: '3.92',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-8DA4',
    feedId: 'whale',
    side: 'LONG',
    symbol: 'TIA/USDT',
    status: 'tested',
    outcome: 'loss',
    pnl: '−3.8%',
    date: 'Jun 6',
    time: '15:09',
    entry: '7.84',
    stop: '7.20',
    tp: '8.6 / 9.4'
  },
  {
    id: 'SIG-8C12',
    feedId: 'whale',
    side: 'LONG',
    symbol: 'ETH/USDT',
    status: 'skipped',
    date: 'Jun 6',
    time: '10:27',
    entry: '3,460',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-8B70',
    feedId: 'whale',
    side: 'SHORT',
    symbol: 'PEPE/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+16.2%',
    date: 'Jun 5',
    time: '18:33',
    entry: '0.0000118',
    stop: '0.0000126',
    tp: '0.0000104 / 0.0000092'
  },
  {
    id: 'SIG-8A05',
    feedId: 'whale',
    side: 'LONG',
    symbol: 'SEI/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+6.5%',
    date: 'Jun 5',
    time: '12:02',
    entry: '0.412',
    stop: '0.378',
    tp: '0.46 / 0.51'
  },
  {
    id: 'SIG-8944',
    feedId: 'whale',
    side: 'LONG',
    symbol: 'WIF/USDT',
    status: 'skipped',
    date: 'Jun 4',
    time: '16:50',
    entry: '2.06',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-8810',
    feedId: 'whale',
    side: 'SHORT',
    symbol: 'ADA/USDT',
    status: 'untested',
    date: 'Jun 4',
    time: '09:14',
    entry: '0.452',
    stop: '0.472',
    tp: '0.428 / 0.404'
  },

  // Apex Crypto Calls (apex)
  {
    id: 'SIG-7F2A',
    feedId: 'apex',
    side: 'LONG',
    symbol: 'BTC/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+12.4%',
    date: 'Jun 6',
    time: '08:42',
    entry: '64,200',
    stop: '62,400',
    tp: '66.5k / 68.2k / 71.0k'
  },
  {
    id: 'SIG-7E18',
    feedId: 'apex',
    side: 'SHORT',
    symbol: 'ETH/USDT',
    status: 'tested',
    outcome: 'loss',
    pnl: '−7.0%',
    date: 'Jun 6',
    time: '09:48',
    entry: '3,420',
    stop: '3,512',
    tp: '3,280 / 3,140'
  },
  {
    id: 'SIG-7D02',
    feedId: 'apex',
    side: 'LONG',
    symbol: 'SOL/USDT',
    status: 'untested',
    date: 'Jun 6',
    time: '13:20',
    entry: '148.5',
    stop: '141.8',
    tp: '158 / 165 / 178'
  },
  {
    id: 'SIG-7C55',
    feedId: 'apex',
    side: 'SHORT',
    symbol: 'DOGE/USDT',
    status: 'skipped',
    date: 'Jun 6',
    time: '14:30',
    entry: '0.1620',
    stop: null,
    tp: null
  },

  // MoonShot Alerts (moon)
  {
    id: 'SIG-6F88',
    feedId: 'moon',
    side: 'LONG',
    symbol: 'PEPE/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+22.5%',
    date: 'Jun 7',
    time: '12:18',
    entry: '0.0000119',
    stop: '0.0000110',
    tp: '0.0000132 / 0.0000148'
  },
  {
    id: 'SIG-6E20',
    feedId: 'moon',
    side: 'LONG',
    symbol: 'WIF/USDT',
    status: 'skipped',
    date: 'Jun 7',
    time: '10:44',
    entry: '2.08',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-6D11',
    feedId: 'moon',
    side: 'SHORT',
    symbol: 'BONK/USDT',
    status: 'skipped',
    date: 'Jun 6',
    time: '17:55',
    entry: '0.0000218',
    stop: null,
    tp: null
  },
  {
    id: 'SIG-6C03',
    feedId: 'moon',
    side: 'LONG',
    symbol: 'FLOKI/USDT',
    status: 'untested',
    date: 'Jun 6',
    time: '11:02',
    entry: '0.000168',
    stop: '0.000154',
    tp: '0.000188 / 0.000210'
  },
  {
    id: 'SIG-6B40',
    feedId: 'moon',
    side: 'LONG',
    symbol: 'SHIB/USDT',
    status: 'skipped',
    date: 'Jun 5',
    time: '15:31',
    entry: '0.0000242',
    stop: null,
    tp: null
  },

  // QuantEdge Research (quant)
  {
    id: 'SIG-5F90',
    feedId: 'quant',
    side: 'LONG',
    symbol: 'BTC/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+9.2%',
    date: 'Jun 7',
    time: '09:30',
    entry: '63,800',
    stop: '62,100',
    tp: '65.9k / 68.0k'
  },
  {
    id: 'SIG-5E44',
    feedId: 'quant',
    side: 'SHORT',
    symbol: 'ETH/USDT',
    status: 'tested',
    outcome: 'loss',
    pnl: '−4.8%',
    date: 'Jun 7',
    time: '08:05',
    entry: '3,440',
    stop: '3,540',
    tp: '3,300 / 3,160'
  },
  {
    id: 'SIG-5D22',
    feedId: 'quant',
    side: 'LONG',
    symbol: 'LINK/USDT',
    status: 'tested',
    outcome: 'profit',
    pnl: '+10.4%',
    date: 'Jun 6',
    time: '14:12',
    entry: '18.60',
    stop: '17.80',
    tp: '20.0 / 21.6'
  },
  {
    id: 'SIG-5C10',
    feedId: 'quant',
    side: 'LONG',
    symbol: 'AAVE/USDT',
    status: 'untested',
    date: 'Jun 6',
    time: '10:48',
    entry: '92.40',
    stop: '87.20',
    tp: '99.0 / 106.5'
  },
  {
    id: 'SIG-5B03',
    feedId: 'quant',
    side: 'SHORT',
    symbol: 'BNB/USDT',
    status: 'skipped',
    date: 'Jun 5',
    time: '16:20',
    entry: '604.0',
    stop: null,
    tp: null
  }
]

/* Map of source ids → display label, used by the Signals page filters. */
export const SOURCES = { telegram: 'Telegram' }

/* ---- Modifier vocabulary — the follow-up actions Verasig parses out of
   reply messages ("close it", "averaging down 2x", "stop to BE…"). ---- */
export const MOD_KINDS = {
  avg_down: { label: 'Avg down', icon: 'arrowDown', tone: 'pending' },
  avg_up: { label: 'Avg up', icon: 'arrowUp', tone: 'pending' },
  partial: { label: 'Partial close', icon: 'target', tone: 'verified' },
  close: { label: 'Close', icon: 'check', tone: 'verified' },
  move_stop: { label: 'Move stop', icon: 'shield', tone: 'info' },
  cancel: { label: 'Cancelled', icon: 'x', tone: 'neutral' }
}

/* ---- Updates that arrived without a reply link — parser couldn't attach them.
   The Signals page surfaces these for manual linking. `suggestId` is the
   heuristic best match (same symbol, most recent open position). ---- */
export const ORPHAN_MODS = [
  {
    id: 'MOD-2263',
    feedId: 'delta',
    symbol: 'ETH',
    date: 'Jun 7',
    time: '14:51',
    text: 'close ETH ✅ out for now',
    suggestId: 'SIG-9E0C',
    reason:
      'Not a reply — closest match is the most recent open ETH position on this feed.'
  }
]

/* What the orphan becomes once the user links it to SIG-9E0C: that position
   already closed at its stop at 14:18, so the late close is recorded but ignored. */
export const ORPHAN_LINKED_MOD = {
  id: 'MOD-2263',
  kind: 'close',
  date: 'Jun 7',
  time: '14:51',
  via: 'manual',
  late: true,
  text: 'close ETH ✅ out for now',
  effect: 'Ignored — position had already closed at its stop (14:18)'
}

/* ---- Verify pass: minimum number of samples a user must confirm before continuing.
   They may verify more (up to every message), but not fewer. ---- */
export const VERIFY_MIN = 6

/* Messages the AI flags as misclassified per verify attempt — these are the catchable
   errors the user should spot. Attempt 1 plants two; attempt >= 2 is clean. */
export const VERIFY_MISCLASSIFIED = {
  1: { m6: 'signal', m13: 'noise', m18: 'signal' } // m6 noise→signal (false +), m13 signal→noise (false −), m18 update→signal (missed link)
}
