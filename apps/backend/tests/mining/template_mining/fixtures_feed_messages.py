"""Python port of the connected-feed demo history (feedMessages.js).

Reshapes the demo seed's Apex feed history into the ChatMessage contract the
miner consumes, matching ``toChatMessages`` + ``FEED_MESSAGES`` in the JS.

Verbatim data port: message texts are the exact seed strings, so E501 is waived
file-wide rather than wrapping (and risking altering) the fixtures.
"""
# ruff: noqa: E501

from __future__ import annotations

FEED_MESSAGES = [
    {
        "id": "m1",
        "date": "Jun 6 08:42",
        "text": "LONG  BTC/USDT\nEntry  64,200 – 63,750\nStop   62,400\nTargets  66.5k / 68.2k / 71.0k\nLeverage  5–10x",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m2",
        "date": "Jun 6 09:03",
        "text": "gm everyone. choppy open, BTC ranging under resistance. patience pays — no FOMO entries here.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m3",
        "date": "Jun 6 09:48",
        "text": "SHORT  ETH/USDT\nEntry  3,420\nSL  3,512\nTP  3,280 / 3,140 / 2,990",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m4",
        "date": "Jun 6 10:15",
        "text": "Join our VIP tier for premium leveraged calls and 1:1 mentoring. Link pinned above.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m5",
        "date": "Jun 6 11:02",
        "text": "SCALP  ARB/USDT long 1.124\nTight stop 1.092\nTarget 1.190\nClose half at 1.16",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m6",
        "date": "Jun 6 11:30",
        "text": "BTC dominance ticking up again, alts bleeding on the lower timeframes. stay nimble.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m7",
        "date": "Jun 6 12:14",
        "text": "Move BTC stop to entry (break-even). First target 66.5k tagged — risk-free from here.",
        "sender": "Apex",
        "reply_to_message_id": "m7-parent",
    },
    {
        "id": "m8",
        "date": "Jun 6 12:41",
        "text": "What are we thinking about the rate decision on Wednesday? drop your bias below 👇",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m9",
        "date": "Jun 6 13:20",
        "text": "LONG  SOL/USDT\nEntry  148.5 – 146.0\nSL  141.8\nTP  158 / 165 / 178\nRisk 2% of book",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m10",
        "date": "Jun 6 13:55",
        "text": "Welcome to all 200 new members this week! Read the pinned rules before posting. 🙌",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m11",
        "date": "Jun 6 14:30",
        "text": "SHORT  DOGE/USDT 0.1620\nSL 0.1685\nTP 0.1540 / 0.1480",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m12",
        "date": "Jun 6 15:02",
        "text": "Markets closed green. Recap thread + this week’s scorecard dropping tonight.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m13",
        "date": "Jun 6 15:48",
        "text": "LONG  LINK/USDT\nEntry 18.40\nSL 17.60\nTP 19.8 / 21.2 / 23.0",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m14",
        "date": "Jun 6 16:20",
        "text": "reminder: never risk more than you can afford. position sizing > everything.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m15",
        "date": "Jun 6 17:05",
        "text": "Close ARB at TP2 1.19 — full position out. +5.9% on the scalp. clean.",
        "sender": "Apex",
        "reply_to_message_id": "m15-parent",
    },
    {
        "id": "m16",
        "date": "Jun 6 17:40",
        "text": "BTC dipping into demand — averaging down 2x at 62,800. Same invalidation, same targets.",
        "sender": "Apex",
        "reply_to_message_id": "m16-parent",
    },
    {
        "id": "m17",
        "date": "Jun 6 18:01",
        "text": "Big week ahead — CPI Wednesday, FOMC minutes Thursday. Expect chop. Size accordingly.",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
    {
        "id": "m18",
        "date": "Jun 6 18:26",
        "text": "out of SOL here +6%. solid day team ✅",
        "sender": "Apex",
        "reply_to_message_id": None,
    },
]
