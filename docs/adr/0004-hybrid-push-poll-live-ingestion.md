# Live ingestion is a hybrid push+poll inside the Telethon adapter

The live listener captures channel messages via a hybrid path inside the Telethon adapter: a passive `events.NewMessage` push handler **plus** a bounded per-channel short-poll loop (2–4s) that actively closes MTProto `pts` gaps, deduplicated on `(channel_id, message_id)`. Capture is queue-first — a `RawTelegramMessage` is persisted immediately and parsing/scoring run asynchronously — so a slow handler never starves the update loop. Telethon stays the single client for both backfill and live. The `TelegramSource` Protocol becomes fully async, and its live method yields a `TelegramDeliveryEvent` tagging each message with its delivery `mode` (`PUSH | POLL | CATCH_UP`) so capture latency is measurable.

We did this after evaluating the operator's reported ~30s delay between a channel message arriving and the handler firing. The root cause is **not** a Telethon defect that a library swap would fix: Telegram batches `UpdateNewChannelMessage` pushes to passive user accounts watching background channels, and a purely passive listener waits out that batching behind unresolved `pts` gaps. Two independent model consultations (Gemini, Codex) plus primary-source research (Telethon issue #652; the v2 `messagebox` gap-handling rewrite ported from `grammers`) converged: the correct fix is architectural — actively close the gap — not Pyrogram-vs-Telethon. Active short-poll is the lightweight equivalent of what TDLib does natively, and it keeps the Stage 0 stack pure-Python with no `libtdjson` in the Docker image.

## Considered options

- **Pyrogram / Pyrofork / Kurigram:** rejected — same MTProto channel batching; a lateral migration that does not address the root cause (upstream Pyrogram is stale; only the forks are maintained).
- **Native TDLib** (`Pytdbot`/`tdjson` — *not* `aiotdlib`, archived Jan 2026): native low-latency gap sync and the lowest ban risk, but a heavy Docker footprint and clunky bulk backfill; **kept as the documented escape hatch** if hybrid polling proves insufficient or scales past dozens of channels.
- **"Foreground emulation"** (fake read-receipts / `getPeerDialogs` to coax real-time push): rejected — a documented account-ban vector and an opaque, breakable heuristic.
- **Bot API** (`aiogram`/`python-telegram-bot`): disqualified — bots cannot read third-party channels they do not administer; niche only (operator alerts on owned channels).
- **Telethon v2 `messagebox`:** tracked, not adopted — it closes gaps natively but ships as `2.0.0a0` (alpha), too unproven to anchor Stage 0.

## Consequences

- The `TelegramSource` Protocol (`data-contracts.md` §9) changes from a sync `backfill()` iterator + `stream()` to async `backfill_batches()` + `live_events()`; the live method emits `TelegramDeliveryEvent`. This supersedes the original seam shape.
- New Stage 0 acceptance metric: median `posted_at → captured_at` ≤ the configured short-poll interval on pilot channels.
- The poll loop covers only the handful of pilot channels, jittered, with flood-wait backoff; scaling to many channels requires revisiting the interval or moving the live adapter to TDLib.
