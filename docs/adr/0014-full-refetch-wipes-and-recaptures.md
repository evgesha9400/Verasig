# Re-fetch full history wipes and recaptures a feed at a chosen history depth

A **Re-fetch full history** (`BackfillMode.FULL`) starts a *new capture
generation*: it verifies the channel still resolves, atomically deletes the
feed's captured messages and their cascaded derived rows, resets the cursor, and
recaptures the channel from scratch — bounded by the feed's chosen **history
depth**. The message counter restarts at zero because progress is recomputed
from the `raw_message` count. It is a **clean wipe** — it secures no deletion
evidence (see the Update below).

Previously FULL only reset the cursor and re-walked the channel, upserting rows
by primary key. Because capture is append-only ([ADR 0001](0001-two-layer-raw-capture.md)),
re-walking never healed in-place edits or removed anything, and the counter kept
climbing from the old total — so "re-fetch full history" silently did almost
nothing a resume didn't. Users needed a real "start this feed's capture over"
action, and a way to capture less than everything.

## Update (2026-07): fetch and deletion detection are decoupled

FULL no longer secures deletion evidence, and **no fetch mode runs the live
deletion rescan**. The operations are now single-purpose:

- **Fetch** (initial backfill, fetch-new, and this wipe & re-fetch) = capture →
  index. A wipe & re-fetch adds only the reachability guard + wipe above.
- **Check gaps** = the live deletion/gap scan plus the signal ("scam") verdict, a
  separate, template-gated operation ([ADR 0008](0008-deletion-evidence-durable-projection.md)).
  It is the *only* place the live channel is walked for deletions.

Rationale: a live rescan finds nothing right after a fresh capture (capture ≈
live) and is the slow step, so running it inside every fetch was wasted work and
conflated "re-download" with "detect deleted signals". A wipe & re-fetch is now a
predictable clean re-download; deletion evidence is preserved deliberately via
Check gaps *before* wiping, when the user wants it.

## Update (2026-07): capture streams newest → oldest

Capture now pages **newest → oldest** (`iter_messages(reverse=False, offset_id=…)`)
so the "oldest message reached" progress date descends from today as the capture
goes back, and the most recent signals land first. Cursor consequences:

- `captured_through_external_message_id` is the **top** (highest/newest) captured
  id. REFRESH pulls messages *above* it; a capture pages *below* the **oldest**
  captured id — derived via `min(external_message_id)`, no new column — down to the
  depth cutoff. Resume-after-crash relies on capture being ON CONFLICT DO NOTHING.
- The depth cutoff is a manual **break** on the older walk (Telethon's
  `offset_date` bounds the wrong end for `reverse=False`): it stops before keeping
  the first message past the cutoff, so nothing out-of-window leaks in.
- REFRESH extends-newer only once the capture has SUCCEEDED; on an incomplete
  capture it resumes the older walk instead of falsely reporting "caught up".

## History depth

A feed remembers a **history depth**: `6m`, `1y` (default), or `all`. A capture
pages newest → oldest and stops once it reaches the depth's cutoff (`183` / `365`
days before now, or no bound for `all`); a resume continues that same older walk,
also bounded by the cutoff. Deepening later is a Re-fetch full history, not a
resume. Depth lives in its own `feed.history_depth` column, **not** in
`feed.metadata`, because a backfill start overwrites the whole `metadata` JSONB.
Telethon walks via `iter_messages(reverse=False, offset_id=…)` and the cutoff is a
manual break on the walk. The Check-gaps gap-span is floored at the oldest stored
id so a depth-limited capture never reports pre-window id gaps as SUSPECTED.

## Wipe safety

The wipe runs inside the backfill job, not synchronously on the request:

1. A lightweight **reachability guard** resolves the channel
   (`resolve_channel`) **before** any row is deleted. If it does not resolve the
   run fails with `ChannelUnreachableError` and **nothing is wiped** — the
   existing capture stays intact and the run is retryable. (This replaced the
   former mandatory pre-wipe evidence rescan; see the Update above. Securing
   deletion evidence is now the separate Check gaps operation.)
2. The wipe is a single transaction: `DELETE FROM raw_message` (events →
   extractions / drift / lifecycle links, and golden labels cascade) plus a
   cursor reset. If it fails, it rolls back whole.
3. Recapture is the normal backfill stream: newest → oldest from the newest
   message down to the chosen depth (the wipe left an empty capture).

## What survives a wipe

FK'd to `feed`, not `raw_message`, so retained across a generation: durable
`DeletedSignalEvidence`, distilled `FilterRule` / `ParserRule`, `backfill_job_run`
history, `feed_risk_config`, `backtest_result`. Cascaded away with the capture:
`raw_message`, `raw_signal_event`, `extracted_signal` / `unrecognized_signal`,
drift warnings, `golden_label`, `lifecycle_link`.

## Considered options

- **Soft-delete / versioned capture generations**: rejected. A per-generation
  tag on every capture and derived row is heavy for a single-user feed whose
  only need is "start over"; the durable evidence already preserves the one
  thing a wipe must not lose.
- **Keep the re-walk-and-upsert status quo**: rejected. It cannot heal edits or
  depth changes, and the counter never resets — the behaviour users reported as
  broken.
- **Bound the rescan's live walk by the rolling depth**: rejected. A message
  older than the cutoff but still live would look absent and fabricate a
  CONFIRMED deletion. The live walk stays full; only fresh *capture* is bounded.

## Consequences

- This **amends the practical reading of [ADR 0001](0001-two-layer-raw-capture.md)**:
  append-only capture still holds *within* a generation; FULL begins a new one.
  It is the mirror of a feed delete + re-add ([ADR 0012](0012-user-owned-generic-source-feed-model.md)),
  minus losing evidence, rules, and run history.
- Golden labels are cascaded away by a wipe (accepted: they are tied to the
  captured messages that no longer exist).
- A FULL against a reviewed (`verified` / `analyzed`) feed keeps that status
  (rules survive); a FULL that aborts because the channel is unreachable marks a
  plain `backfilled` feed `failed`, with its capture untouched and retryable.
