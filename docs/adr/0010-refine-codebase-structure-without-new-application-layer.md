# Refine codebase structure without adding a new application layer

We will keep the current responsibility-based package shape and refine its boundaries instead of introducing numbered workflow folders, a generic `capabilities/` package, or a new top-level `application/` layer.

The target direction is:

- `domain/` remains the pure contract package and becomes the single catalog for Protocol seams.
- `services/` remains feature-cohesive and keeps both pure logic and thin orchestration files together when they change together.
- `foundation/` is clarified as the concrete IO edge: external adapters plus database/session setup. `storage/` remains a sibling persistence edge for ORM rows and repositories.
- File names must make purity explicit: pure modules use names like `diff`, `fold`, `hygiene`, `scorecard`, `deterministic_parser`; IO orchestration modules use names like `backfill`, `live`, `rescan`, `extract_service`.
- Protocol definitions are centralized away from concrete adapters so importing a seam never imports heavy IO libraries such as Telethon or httpx.

We chose this because the codebase already documents the dependency rule `domain/` (pure contracts) -> `services/` (logic) -> `storage/` + `foundation/` (IO), and the current friction is narrower than a full restructuring. The real defects are that `foundation/` is vague, Protocol seams are scattered across files that also contain concrete drivers, and the pure-vs-orchestration distinction is not obvious enough from file names.

This keeps the repo aligned with the observer spec's local, one-image MVP while preserving the future path to separate deployable workers later if the product validates. It also keeps feature-local work ergonomic: capture, extraction, deletion, lifecycle, distillation, simulation, and scoring stay easy to reason about without spreading one feature across `application/`, `services/`, and `adapters/`.

## Considered options

- **Numbered workflow folders** (`01_capture`, `02_candidates`, ...): rejected because Verasig is not a strict line. The flow branches, loops, and recomputes: distillation feeds back into extraction, scoring reads many evidence classes, deletion observes ephemeral live state, and live ingestion is continuous. Numbered folders would create false order, renaming churn, and import noise. Numbering belongs in implementation plans and diagrams, not Python package names.
- **Generic `capabilities/` package**: rejected because the term is a synonym for feature and is not more precise than `services/`. It risks becoming the same kind of vague bucket as `foundation`. The useful names are the children (`ingestion`, `extraction`, `deletion`, `scoring`), which already exist.
- **Full application split** (`domain/`, `services/`, `application/`, `adapters/`, `entrypoints/`): viable but deferred. It gives a strong ports-and-adapters shape, but for this codebase it would split tightly related feature work across too many folders and add churn before the MVP needs it.
- **Deployable package split** (`packages/`, `apps/`, `workers/`): rejected for now. The business docs say the platform is the end state, not the MVP. The current observer is a local, one-image system.

## Consequences

- `foundation/` is documented as concrete external adapters plus DB/session setup, so it no longer overlaps ambiguously with `storage/`.
- `storage/` remains a sibling persistence edge for SQLAlchemy ORM rows and repositories.
- Protocols live in the pure `domain/protocols.py` home, with event contracts such as `TelegramDeliveryEvent` and `TelegramDeletionEvent` in pure domain modules.
- Concrete adapters import and implement Protocols, not define them beside heavy IO dependencies.
- Foundation adapter filenames now name their concrete implementations: `telethon_source.py`, `bybit_market_data.py`, and `static_exchange.py`.
- `services/` modules should be audited for naming clarity. Pure cores and orchestration wrappers may live in the same feature package, but the file names must disclose which role they play.
- Any later full application split should be justified by concrete growth pressure, not by aesthetic layering.
- The next implementation pass should be small and mechanical: finish the service-file naming audit and rename only where the current name hides purity or IO.
