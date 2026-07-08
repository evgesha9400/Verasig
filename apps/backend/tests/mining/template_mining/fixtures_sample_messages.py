"""Python port of ``sampleMessages.js`` - bundled sample history fixtures.

A representative spread of real Telegram signal formats with repeats, plus the
updates, results, commentary and noise the miner must downgrade or drop. Used
as the strongest parity anchor for ``mine_template_groups``.

Verbatim data port: message texts are the exact JS source strings, so E501 is
waived file-wide rather than wrapping (and risking altering) the fixtures.
"""
# ruff: noqa: E501

from __future__ import annotations

# A minimal signal family - three messages, one format.
SIGNAL_FAMILY = [
    {
        "id": "s1",
        "date": "2026-06-01",
        "text": "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355",
    },
    {
        "id": "s2",
        "date": "2026-06-02",
        "text": "XAUUSD BUY NOW\nSL 2305\nTP 2330\nTP 2350",
    },
    {
        "id": "s3",
        "date": "2026-06-03",
        "text": "XAUUSD BUY NOW\nSL 2300\nTP 2325\nTP 2345",
    },
]


def _sample(date: str, text: str, _seq=[0]) -> dict:  # noqa: B006
    _seq[0] += 1
    return {"id": f"sample-{_seq[0]}", "date": date, "sender": "channel", "text": text}


SAMPLE_MESSAGES = [
    # Family A - XAUUSD market order, two take profits
    _sample("2026-05-04", "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"),
    _sample("2026-05-06", "XAUUSD BUY NOW\nSL 2305\nTP 2332\nTP 2350"),
    _sample("2026-05-09", "XAUUSD BUY NOW\nSL 2298\nTP 2325\nTP 2342"),
    _sample("2026-05-12", "XAUUSD SELL NOW\nSL 2360\nTP 2330\nTP 2312"),
    # Family B - emoji header, entry range, numbered TPs
    _sample(
        "2026-05-05", "\U0001f7e2 GOLD\nEntry 2320-2325\nSL 2312\nTP1 2340\nTP2 2355"
    ),
    _sample(
        "2026-05-08", "\U0001f7e2 GOLD\nEntry 2331-2336\nSL 2322\nTP1 2352\nTP2 2368"
    ),
    _sample(
        "2026-05-11",
        "\U0001f534 EURUSD\nEntry 1.0860-1.0855\nSL 1.0900\nTP1 1.0820\nTP2 1.0800",
    ),
    _sample(
        "2026-05-14", "\U0001f7e2 GOLD\nEntry 2344-2349\nSL 2335\nTP1 2366\nTP2 2380"
    ),
    # Family C - EURUSD inline range sell
    _sample("2026-05-04", "Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800"),
    _sample("2026-05-07", "Sell EURUSD 1.0910-1.0920\nSL 1.0955\nTP 1.0850"),
    _sample("2026-05-10", "Sell GBPUSD 1.2680-1.2690\nSL 1.2730\nTP 1.2610"),
    # Family D - lowercase market call with stop-below and a target list
    _sample("2026-05-05", "Gold long now\nStop below 2312\nTargets 2340 / 2355"),
    _sample("2026-05-09", "Gold long now\nStop below 2326\nTargets 2352 / 2370"),
    _sample("2026-05-13", "Bitcoin long now\nStop below 66400\nTargets 69000 / 70500"),
    # Family E - index sell zone with invalidation and a space-separated target list
    _sample(
        "2026-05-06",
        "NAS100 SELL ZONE 19800-19850\nInvalidation 19920\nTargets 19720 19650 19500",
    ),
    _sample(
        "2026-05-12",
        "NAS100 SELL ZONE 20050-20100\nInvalidation 20180\nTargets 19960 19880 19720",
    ),
    # Family F - crypto market long, no entry, SL + two TPs
    _sample("2026-05-04", "BTC LONG\nSL 67400\nTP 69000\nTP 70500"),
    _sample("2026-05-08", "BTC LONG\nSL 66100\nTP 68200\nTP 69800"),
    _sample("2026-05-11", "ETH LONG\nSL 3320\nTP 3520\nTP 3680"),
    # Family G - @ entry, single TP
    _sample("2026-05-07", "GBPJPY short @ 192.50\nSL 193.20\nTP 191.80"),
    _sample("2026-05-13", "GBPJPY short @ 193.80\nSL 194.40\nTP 192.90"),
    # Family H - crypto pair with en-dash entry range and slash target list
    _sample(
        "2026-05-05",
        "LONG BTC/USDT\nEntry 64200 – 63750\nStop 62400\nTargets 66500 / 68200 / 71000",
    ),
    _sample(
        "2026-05-10",
        "SHORT ETH/USDT\nEntry 3550 – 3580\nStop 3620\nTargets 3480 / 3400",
    ),
    # Family I - equities options
    _sample("2026-05-06", "AAPL CALL above 210\nSL 205\nTP 220"),
    _sample("2026-05-09", "TSLA PUT 180\nSL 186\nTP 170"),
    # Updates - adjustments to an open position (must be downgraded)
    _sample("2026-05-04", "Move SL to BE on gold buy"),
    _sample("2026-05-05", "Close BTC long now"),
    _sample("2026-05-07", "Cancel EURUSD sell"),
    _sample("2026-05-09", "Move stop to entry on the NAS100 short"),
    # Results - the trade already played out (must be downgraded)
    _sample("2026-05-05", "XAUUSD BUY hit TP1 ✅"),
    _sample("2026-05-06", "ETH short hit SL"),
    _sample("2026-05-08", "US30 buy closed +150 points"),
    _sample("2026-05-10", "BTC long running +300 pips"),
    _sample("2026-05-12", "GOLD buy smashed all targets, +420 pips \U0001f680"),
    # Commentary - directional opinion without a tradeable structure
    _sample("2026-05-04", "Gold looks bullish today but wait for confirmation"),
    _sample("2026-05-06", "XAUUSD analysis: price may reject from 2330"),
    _sample("2026-05-11", "Thinking EURUSD could be bearish into the London session"),
    # Noise - not signals at all
    _sample("2026-05-04", "Good morning team, waiting for NY session"),
    _sample(
        "2026-05-05",
        "Join our VIP tier for premium leveraged calls. Link pinned above.",
    ),
    _sample("2026-05-07", "gm everyone — choppy open, patience pays. no FOMO entries."),
    _sample(
        "2026-05-09",
        "Welcome to all the new members this week! \U0001f64c Read the pinned rules.",
    ),
    _sample(
        "2026-05-13", "Big week ahead — CPI Wednesday, FOMC Thursday. Expect chop."
    ),
]
