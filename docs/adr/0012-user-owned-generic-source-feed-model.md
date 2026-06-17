# Collapse the shared-channel cache into a user-owned, provider-agnostic Source→Feed model

The capture layer is rebuilt as a **user-owned, provider-agnostic** two-level model:
a **`source`** (a user's connection to a provider) exposes **`feed`s** (the streams that
user follows), whose captured **`raw_message`s** and every derived row are all keyed by
`user_id`. Provider ids are stored generically as `external_id` / `external_message_id`;
"Telegram" survives only in code (the single adapter) and in data (`source.config`,
`feed.metadata`), never in a table or column name. Deleting a feed — or the source above
it — cascades away all of that user's capture and derived rows, so a re-add starts a clean
backfill from a NULL cursor.

We did this because the backend was built as a multi-tenant **shared "channel cache"**
(`telegram_channel` + `user_channel` membership, globally keyed by `channel_id`), which
produced two defects:

1. **Delete didn't delete.** `unsubscribe()` dropped the user's derived rows and the
   `user_channel` link but kept the downloaded `raw_telegram_message`s **and** the backfill
   cursor (cursor lived on the shared `telegram_channel`). Re-adding a channel resumed from
   the stale cursor instead of starting clean (observed: a re-added channel restarted at
   message 5000).
2. **Inconsistent, Telegram-flavoured naming** for one concept across every layer
   (`telegram_channel`/`user_channel`/`chat_risk_config`/`channel_id`/`message_id`).

Capture runs through **each user's own Telegram session** and supports **private channels**,
so raw capture is inherently per-user-session — there is no shared, global truth to cache.
That makes **user-owned** storage the correct model, not an optimization: the shared cache
was modelling a multi-tenant assumption the product never had (single-user, pre-launch).

## Considered options

- **Keep the shared/global channel cache (status quo)**: rejected. It caused both bugs
  above, and it is simply wrong for per-user-session capture of private channels — two users
  authorized to the same private channel can legitimately hold different captured histories,
  so a single global `telegram_channel` row cannot represent them.
- **User-owned capture (chosen, "A2")**: every capture + derived table carries `user_id`;
  composite FKs root at `feed(user_id, external_id)`; `delete_feed` is a single
  `DELETE FROM feed …` that cascades. This makes delete-actually-deletes a property of the
  schema rather than of an easily-forgotten service loop.
- **Keep Telegram-named tables, just add `user_id`**: rejected. It fixes the delete bug but
  not the naming, and entrenches the assumption that the only provider is Telegram. A
  generic `source`/`feed`/`raw_message` model with `external_id` columns costs nothing today
  (BigInt fits Telegram/Discord ids) and leaves "Telegram" as one swappable adapter.
- **Three-level model (account → source → channel → feed)**: rejected as over-structured for
  a single provider. Two levels — `source` (connection) → `feed` (followed stream) — carry
  the cascade and the provider-agnosticism without a redundant tier.
- **One big migration vs. two**: split into **`0010`** (user-owned merged `feed`/`raw_message`
  + `external_id` renames) and **`0011`** (generic `source` + `feed.source_id`). Each is
  independently reviewable and forward-only; the merge that drops `telegram_channel` /
  `user_telegram_link` is destructive, so neither offers a downgrade.

## Consequences

- **New / changed tables.** `feed` [merge of `user_channel` + `telegram_channel`, PK
  `(user_id, external_id)`, cursor `captured_through_external_message_id`, `metadata` JSONB];
  `raw_message` [rename of `raw_telegram_message`]; `source` [replaces `user_telegram_link`,
  `name` CHECK `('Telegram')`, `config_encrypted` JSONB]; `feed_risk_config` [rename of
  `chat_risk_config`]. `external_id` / `external_message_id` replace `channel_id` /
  `message_id` in storage everywhere.
- **Cascade delete is structural.** Composite `ON DELETE CASCADE` FKs root every
  channel-scoped table at `feed(user_id, external_id)`; `feed.source_id → source` cascades a
  whole connection's feeds. `delete_feed(user_id, external_id)` therefore purges this user's
  messages, events, derived rows, evidence, and the cursor; a re-add inserts a fresh `feed`
  (NULL cursor) → full refetch. Fixes bug 1.
- **The domain keeps its Telegram vocabulary.** In code, `TelegramChannel`,
  `RawTelegramMessage`, `RawSignalEvent`, `GoldenLabel`, etc. still speak `channel_id` /
  `message_id` / `cursor_message_id`. The **repository layer is the only translation
  boundary** to the generic `external_id` / `external_message_id` storage columns. We did not
  rename the domain: the canonical vocabulary ([CONTEXT.md](../context/CONTEXT.md)) is sound,
  and churning value objects + every test for a storage rename would be cost without benefit.
- **Telegram is one adapter.** `features/sources/telegram_adapter.py` (connect / verify /
  status + `read_connection`) reads and writes the generic `source` row; the secrets live in
  `source.config_encrypted` as a JSON document whose sensitive fields stay AES-GCM envelopes
  (the codec, and the per-user AAD, live in the adapter — migration `0011` carries the
  existing envelopes verbatim, re-encrypting nothing).
- **Folder structure mirrors the model.** `features/sources/` = the connection layer
  (`source_repository` + the Telegram adapter); `features/feeds/` = the stream layer
  (`feed_repository`, `feed_views`, `message_repository`, backfill, deletion, …).
- **API + UI speak "feed".** The HTTP surface is `/feeds` (was `/chats`), the not-found code
  is `FEED_NOT_FOUND`, and the frontend follows `feeds` / `activeFeedId`. "chat" is retired
  from the wire.
- **Narrows [ADR 0008](0008-deletion-evidence-durable-projection.md).** `DeletedSignalEvidence`
  is now `user_id`-scoped and cascades on feed delete, so its "durable, non-recomputable"
  guarantee is scoped to **the feed's lifetime** — deleting a feed discards its deletion
  evidence along with the capture it described. Re-adding the feed rebuilds evidence from a
  fresh rescan. See that ADR's amendment.
