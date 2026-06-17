# Source Workflow Requirements

## Purpose

- Verasig is a signal verification SaaS platform.
- V1 guides a user from source connection to provider evidence.
- V1 supports Telegram as the first Signal Source.
- V1 supports Bybit as the first Destination.
- Discord is shown as Coming soon.
- Binance is shown as Coming soon.
- A connected Signal Source is a `Source`; the streams a user follows through it are `Feed`s (the `/feeds` API + UI term). "chat" is retired.
- In-code domain language remains `TelegramChannel`; it is persisted as a user-owned `feed` row. See [CONTEXT.md](../../context/CONTEXT.md) and [ADR 0012](../../adr/0012-user-owned-generic-source-feed-model.md).

## User Stories

- As a user, I see configured Signal Sources.
- As a user, I see Signal Sources that can be configured.
- As a user, I configure Telegram with API ID, API hash, and phone number.
- As a user, I enter the Telegram verification code to complete setup.
- As a user, I open Telegram after setup.
- As a user, I see available Telegram channels.
- As a user, I see each channel name.
- As a user, I see each channel subscriber count.
- As a user, I see each public channel handle.
- As a user, I start channel backfill.
- As a user, I see backfill progress while historical messages are captured.
- As a user, I cancel active backfill.
- As a user, I retry canceled backfill from the last saved message.
- As a user, I open the label, distill, verify loop after backfill completes.
- As a user, I label messages as Signal or Non-signal.
- As a user, I classify messages with left and right arrow keys.
- As a user, I move between messages with up and down arrow keys.
- As a user, I return to the previous message to correct accidental labels.
- As a user, I see message text.
- As a user, I see message media when media exists.
- As a user, I see labeled messages colored by their selected label.
- As a user, I can start distillation after labeling at least 5 Signal messages.
- As a user, I wait while AI distills provider-specific rules.
- As a user, I verify randomly sampled messages classified as Signal.
- As a user, I mark sampled classifications as correct or wrong.
- As a user, I continue the label, distill, verify loop when verification fails.
- As a user, I proceed when verification passes.
- As a user, I connect Bybit as the first Destination.
- As a user, I enter Bybit API secrets.
- As a user, I see Bybit connection verification.
- As a user, I configure fallback risk management when extracted signals have no risk management.
- As a user, I choose signal risk management when extracted signals include it.
- As a user, I optionally configure fallback risk management even when signals include it.
- As a user, I wait while backtests run.
- As a user, I see signal quality analysis.
- As a user, I see a ProviderScore beside analyzed channels.
- As a user, I fetch new messages after analysis.
- As a user, I restart a channel workflow by deleting its backfill.

## Workflow

```text
Sources
  -> Telegram setup
  -> Telegram channels
  -> Backfill
  -> Label
  -> Distill
  -> Verify
  -> Extract
  -> Destination setup
  -> Risk policy
  -> Backtest
  -> ProviderScore
```

## Source Setup

| Step | Screen | Requirement |
|---|---|---|
| 1 | Sources | Show configured sources first. |
| 2 | Sources | Show Telegram as configurable when it is not connected. |
| 3 | Sources | Show Discord as Coming soon. |
| 4 | Telegram setup | Collect API ID. |
| 5 | Telegram setup | Collect API hash. |
| 6 | Telegram setup | Collect phone number. |
| 7 | Telegram setup | Send Telegram verification code. |
| 8 | Telegram verification | Collect verification code. |
| 9 | Telegram verification | Mark Telegram as configured after successful verification. |

## Channel List

| Field | Requirement |
|---|---|
| Name | Show the TelegramChannel title. |
| Subscribers | Show subscriber count as an active-user proxy. |
| Handle | Show the public `@handle` when available. |
| Private | Show private-channel status when no handle exists. |
| State | Show backfill, labeling, verification, extraction, analysis, and restart states. |
| Score | Show ProviderScore only after analysis exists. |

## Backfill

| State | Requirement |
|---|---|
| Not started | Show Start backfill. |
| Running | Show fetched message count. |
| Running | Show date of the last fetched message. |
| Running | Use an indeterminate loader. |
| Running | Do not imply a known total message count. |
| Running | Show Cancel. |
| Canceled | Return to channel list. |
| Canceled | Show Retry. |
| Retry | Resume from the last saved `RawTelegramMessage`. |
| Complete | Open the label, distill, verify loop. |

## Label

| Control | Requirement |
|---|---|
| Left arrow | Label current message Non-signal. |
| Right arrow | Label current message Signal. |
| Up arrow | Move to previous message. |
| Down arrow | Move to next message. |
| Signal button | Label current message Signal. |
| Non-signal button | Label current message Non-signal. |
| Previous message | Allow correction of accidental labels. |
| Signal color | Tint labeled Signal messages with the signal color. |
| Non-signal color | Tint labeled Non-signal messages with the non-signal color. |

## Distill

| Rule | Requirement |
|---|---|
| Minimum examples | Enable distillation after at least 5 Signal labels. |
| Inputs | Use the user-labeled golden corpus. |
| Output | Generate provider-specific `FilterRule`s. |
| Output | Generate provider-specific `ParserRule`s. |
| Progress | Show AI distillation running state. |
| Completion | Move to verification sampling. |

## Verify

| Step | Requirement |
|---|---|
| 1 | Present random historical messages classified as Signal. |
| 2 | Ask the user to confirm each classification. |
| 3 | Record correct classifications. |
| 4 | Record wrong classifications. |
| 5 | Continue labeling when verification fails. |
| 6 | Continue distillation when verification fails. |
| 7 | Continue verification when verification fails. |
| 8 | Proceed to extraction when verification passes. |

## Extraction

| Step | Requirement |
|---|---|
| 1 | Extract all messages after verification passes. |
| 2 | Produce `ExtractedSignal` records for recognized trade intent. |
| 3 | Preserve `UnrecognizedSignal` outcomes for parser gaps. |
| 4 | Preserve traceability from extracted output to `RawTelegramMessage`. |

## Destination Setup

| Step | Screen | Requirement |
|---|---|---|
| 1 | Destinations | Show Bybit as configurable in V1. |
| 2 | Destinations | Show Binance as Coming soon. |
| 3 | Bybit setup | Collect required Bybit API secrets. |
| 4 | Bybit setup | Verify the Bybit connection. |
| 5 | Bybit setup | Proceed only after verification succeeds. |

## Risk Policy

| Signal state | Requirement |
|---|---|
| Signals include risk management | Offer signal risk management. |
| Signals include risk management | Offer optional fallback risk management. |
| Signals lack risk management | Require user-configured fallback risk management. |
| Any policy | Show that the first supported outcome is observe-only analysis. |

## Analysis

| Step | Requirement |
|---|---|
| 1 | Run backtests after destination and risk setup. |
| 2 | Analyze signal quality from simulated outcomes. |
| 3 | Show ProviderScore beside analyzed TelegramChannels. |
| 4 | Link ProviderScore to ProviderScoreExplanation. |
| 5 | Allow fetching new messages at any point. |
| 6 | Allow complete restart by deleting channel backfill. |

## UI Constraints

- The primary review surface is dark theme.
- The Sources page is the workflow entry point.
- Telegram is the only configurable V1 source.
- Discord is visible only as Coming soon.
- Bybit is the only configurable V1 destination.
- Binance is visible only as Coming soon.
- Label actions are exactly Signal and Non-signal.
- Noise is not a third label.
- Raw Telegram messages can be long and multiline.
- Message line breaks must be preserved.
- Message media must be visible when present.
- Chrome must stay compact to maximize visible messages.
- The label review surface must preserve keyboard navigation.
- Green, red, amber, and blue must only encode measured state.
- Subscriber count must be labelled as a proxy.

## Acceptance Criteria

- [ ] User can configure Telegram with API ID, API hash, phone number, and verification code.
- [ ] Sources page shows configured sources and configurable sources.
- [ ] Sources page shows Telegram available and Discord Coming soon.
- [ ] Telegram page lists available TelegramChannels.
- [ ] Channel rows show title, subscriber count, handle or private state, workflow state, and score when analyzed.
- [ ] Backfill progress shows fetched count and last fetched message date.
- [ ] Backfill loader is indeterminate.
- [ ] Cancel returns the user to the channel list.
- [ ] Retry resumes from the last saved message.
- [ ] Completed backfill opens the label, distill, verify loop.
- [ ] Left and right arrows classify Signal and Non-signal.
- [ ] Up and down arrows move between messages.
- [ ] User can correct accidental labels.
- [ ] Distillation unlocks after at least 5 Signal labels.
- [ ] Verification presents random messages classified as Signal.
- [ ] Verification failure returns the user to label, distill, verify.
- [ ] Verification success starts extraction.
- [ ] Destination setup shows Bybit available and Binance Coming soon.
- [ ] Bybit setup verifies required API secrets.
- [ ] Missing signal risk management requires fallback risk management.
- [ ] Signal risk management can be used with optional fallback.
- [ ] Backtests run after destination and risk setup.
- [ ] ProviderScore appears beside analyzed channels.
- [ ] User can fetch new messages after analysis.
- [ ] User can delete backfill and restart the channel workflow.
