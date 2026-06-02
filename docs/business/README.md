# Verasig Business Pack

## Project Name

- Parent platform: `Deltalytic`.
- Standalone product direction: `Verasig`.
- Tagline: proof-first signal provider intelligence.

## Decision

- Build separate wedges.
- Validate each wedge independently.
- Keep shared contracts compatible with one future platform.
- Do not launch the full agentic trading platform first.

## Recommended Wedge

- First wedge: `Verasig`.
- First user: operator.
- First buyer: trader paying for proof.
- Second buyer: signal channel owner.
- First source: Telegram app user-account session.
- First active execution mode: demo.
- First value: prove whether a signal source actually performs.

## Why This Wedge

- It is narrow enough to ship.
- It reuses current Deltalytic architecture.
- It creates proprietary data.
- It avoids starting as generic quant infrastructure.
- It avoids starting as generic AIOps infrastructure.
- It gives auto-research a future signal dataset.

## Documents

- [market-research.md](market-research.md) - market evidence and competitor map.
- [business-decomposition.md](business-decomposition.md) - separate products and sequencing.
- [value-proposition.md](value-proposition.md) - core buyer, pain, promise, and pricing hypotheses.
- [requirements.md](requirements.md) - user stories and open questions.
- [core-features.md](core-features.md) - MVP scope and deferred scope.
- [validation-stages.md](validation-stages.md) - MVP to scale evaluation path.
- [architecture-decisions.md](architecture-decisions.md) - business-facing architecture decisions.
- [project-structure.md](project-structure.md) - folder and document protocol.
