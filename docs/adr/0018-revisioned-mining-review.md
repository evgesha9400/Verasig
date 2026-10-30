# Revision Mining decisions against immutable review input

Template-mining decisions now address a persisted **MiningReview** by `reviewId`.
Each review freezes the exact ordered message corpus, mined template families,
and parser overlay shown to the operator. Its `inputRevision` is a SHA-256 digest
of the ordered message identity/text/date, the overlay, and the feed's capture
generation. Re-fetching full history advances that generation even when the
recaptured bytes are identical.

Audit and Confirm load the addressed review rather than re-mining current raw
messages. They recompute the live input revision first; a changed corpus,
overlay, or capture generation returns `409 MINING_REVIEW_STALE` and performs no
signal or feed-status mutation. The old singleton `mine_result` cache had no
input identity, so migration `0002_revisioned_mining_review` drops it instead of
promoting unsafe cached payloads and creates the append-only `mining_review`
table.

Confirm locks the feed row before validating the review. Replacing the feed's
signal projection, recording confirmed-review evidence, and setting
`FeedStatus.VERIFIED` share one database transaction. Backfill run creation uses
the same feed-row lock, so Confirm either commits before a backfill starts or
observes `BACKFILLING` and conflicts; it cannot interleave a partial projection
or status transition with capture startup.

`parser_confidence` remains the ADR 0017 recognition-rate component. Its misses
are now the stable message ids in the exact confirmed review's candidate audit:
ambiguous candidates, rare template candidates, and potential misses, excluding
rejected updates/results, generic chatter, and any message that produced a
persisted signal. Provider-score evidence refers to those rows as
`message:{feed_id}/{message_id}`.

## Consequences

- Preview and cached result payloads expose `reviewId` and `inputRevision`.
- Audit and Confirm requests require `reviewId`.
- A stale result cannot hydrate Verify as current; the UI requires a fresh mine.
- Historical reviews survive capture changes for explicit stale detection and
  confirmed scoring evidence, then cascade when their feed is deleted.
- No application layer, global job coordinator, or client-side parser is added;
  the seam remains local to Mining and the existing feed transaction boundary.
