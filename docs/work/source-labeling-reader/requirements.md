# Source Labeling Reader Requirements

## User Stories

- As a user, I connect Telegram as the first supported source.
- As a user, I load all available Telegram chats after connection.
- As a user, I select one chat to backfill.
- As a user, I see backfill progress while historical messages are imported.
- As a user, I open the selected chat in a labeling reader.
- As a user, I see messages ordered newest to oldest.
- As a user, I label each message as either Signal or Non-signal.
- As a user, I can label the highlighted message with keyboard shortcuts on macOS and Windows.
- As a user, I can move the highlighted message with keyboard navigation.
- As a user, I see labeled, signal, non-signal, and unlabeled counts above the list.
- As a user, I filter by candidates, non-candidates, unlabeled, signal, non-signal, media, and replies.
- As a user, I page through messages with 100 messages as the default page size.
- As a user, I initiate distillation after enough messages are labeled.
- As a user, I see distillation progress.
- As a user, I see final signal and non-signal stats after distillation.

## UI Constraints

- The primary review surface is dark theme.
- V1 source UI shows Telegram only.
- Future source examples must not appear until confirmed.
- Label actions are exactly Signal and Non-signal.
- Noise is not a third label.
- The message list column order is Source msg id, Posted, Captured, Type, Message, Buttons.
- The top visible row is highlighted by default.
- Signal rows are tinted with the signal color after labeling.
- Non-signal rows are tinted with the non-signal color after labeling.
- Raw Telegram messages can be long and multiline.
- Message line breaks must be preserved.
- Chrome must stay compact to maximize visible messages.
- The review table sits in a narrower central column to reduce left-right eye travel.
- Label buttons stay immediately after the message column.
