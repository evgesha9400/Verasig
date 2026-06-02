# Two-layer raw capture: RawTelegramMessage vs RawSignalEvent

We split raw capture into two layers: `RawTelegramMessage` (every message, immutable, append-only — the 100%-capture truth) and `RawSignalEvent` (the subset a cheap candidate filter flags as a signal candidate, plus the text slice fed to extraction). This supersedes `project-structure.md`'s original naming, where `RawSignalEvent` alone meant "original source content."

We did this so capture-completeness is measured on `RawTelegramMessage` while extraction precision/recall is measured on `RawSignalEvent`, and so off-topic chatter never pollutes the signal pipeline. A future reader seeing two near-identical tables should know the split is deliberate, not accidental duplication.

## Considered options

- **Collapse to one** (`RawSignalEvent` = raw capture, as the old docs said): rejected because then every chatter message is a "SignalEvent" and the name lies; capture vs candidate metrics blur.
- **Event-sourced lifecycle** (`RawSignalEvent` = CREATED/EDITED/DELETED event stream): rejected because it overlaps `DeletedSignalEvidence`, which we keep as its own first-class entity.
