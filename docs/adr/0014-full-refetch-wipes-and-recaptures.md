# Re-fetch full history wipes and recaptures a feed at a chosen history depth

A **Re-fetch full history** (`BackfillMode.FULL`) starts a *new capture
generation*: it secures deletion evidence, atomically deletes the feed's
captured messages and their cascaded derived rows, resets the cursor, and
recaptures the channel from scratch — bounded by the feed's chosen **history
depth**. The message counter restarts at zero because progress is recomputed
from the `raw_message` count.

Previously FULL only reset the cursor and re-walked the channel, upserting rows
by primary key. Because capture is append-only ([ADR 0001](0001-two-layer-raw-capture.md)),
re-walking never healed in-place edits or removed anything, and the counter kept
climbing from the old total — so "re-fetch full history" silently did almost
nothing a resume didn't. Users needed a real "start this feed's capture over"
action, and a way to capture less than everything.

## History depth

A feed remembers a **history depth**: `6m`, `1y` (default), or `all`. A *fresh*
capture (NULL cursor) stops once it reaches the depth's cutoff (`183` / `365`
days before now, or no bound); a resume is cursor-bound and ignores the cutoff.
Deepening later is therefore a Re-fetch full history, not a resume. Depth lives
in its own `feed.history_depth` column, **not** in `feed.metadata`, because a
backfill start overwrites the whole `metadata` JSONB. Telethon applies the bound
via `iter_messages(reverse=True, offset_date=cutoff)`, which composes with the
`min_id` cursor. The deletion gap-span is floored at the oldest stored id so a
depth-limited capture never reports pre-window id gaps as SUSPECTED deletions.

## Wipe safety

The wipe runs inside the backfill job, not synchronously on the request:

1. A mandatory **pre-wipe rescan** ([ADR 0008](0008-deletion-evidence-durable-projection.md))
   re-reads the live channel and persists CONFIRMED deletions with their
   original text **before** any row is deleted. An empty live snapshot raises
   `RescanAborted` here, so an inaccessible channel fails the run and **nothing
   is wiped** — the existing capture stays intact and the run is retryable.
2. The wipe is a single transaction: `DELETE FROM raw_message` (events →
   extractions / drift / lifecycle links, and golden labels cascade) plus a
   cursor reset. If it fails, it rolls back whole.
3. Recapture is the normal backfill stream, now from a NULL cursor at the chosen
   depth.

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
  (rules survive); a FULL that aborts on an empty live snapshot marks a plain
  `backfilled` feed `failed`, with its capture untouched and retryable.
