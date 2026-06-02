# Validation Stages

## Stage 0 - Operator Dogfood

- Run against operator-selected Telegram sources.
- Store every raw event.
- Parse text-only signals.
- Produce observe-only channel scorecards.
- Do not execute orders.
- Pass gate: operator can identify one good, bad, or untradeable signal source from stored evidence.

## Stage 1 - Local MVP

- Run locally or in the cheapest safe dev environment.
- Use captured Telegram messages for deterministic tests.
- Use real captured messages for parser evaluation.
- Pass gate: 1,000 raw messages processed with measurable parser precision and recall.

## Stage 2 - Cheap Cloud MVP

- Deploy Telegram app ingestion, Signal Lake, and provider scorecard.
- Keep one user.
- Keep one region.
- Keep observe-only mode.
- Pass gate: no missing raw events and no missing score evidence.

## Stage 3 - Pilot Interest

- Recruit 3 to 5 traders or channel owners.
- Show evidence-backed scorecards.
- Do not support live execution yet.
- Pass gate: 2 pilots ask to keep using it after seeing their own data.

## Stage 4 - Paid Beta

- Add billing only after pilots repeat usage.
- Gate by channels, events, backtest runs, and scorecard exports.
- Keep live execution behind manual review.
- Pass gate: first recurring revenue without promising returns.

## Stage 5 - Research Integration

- Feed Signal Lake into auto-research.
- Build filters that decide when a source signal should be ignored.
- Compare passthrough against decision strategies.
- Pass gate: filtered strategy beats passthrough on out-of-sample demo data.

## Stage 6 - Live Execution

- Add live mode only after demo proof and compliance review.
- Require explicit user controls.
- Require hard risk caps.
- Require full audit export.
- Pass gate: every live-affecting action is reconstructable from stored records.

## Stage 7 - Platform Scale

- Add Discord.
- Add image and multimodal extraction.
- Add multi-user tenancy.
- Add regional data planes.
- Add portfolio allocation.
- Add unified GUI.
- Pass gate: unit economics remain positive per user and per region.
