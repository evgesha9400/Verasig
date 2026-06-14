# Verasig prototype — documentation

Reference docs for the product flows mocked in this prototype. These describe **intended behavior** — the prototype implements the UI; engine behavior is specified here for future implementation.

| Doc                                                    | Contents                                                                          |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- |
| [pipeline-flow.md](pipeline-flow.md)                   | The end-to-end feed onboarding pipeline: screens, transitions, feed statuses      |
| [execution-step.md](execution-step.md)                 | The Execution step (formerly "Risk"): model, sections, controls, design decisions |
| [execution-adaptivity.md](execution-adaptivity.md)     | Corpus-driven display gates + per-signal engine matrix (decision tree)            |
| [execution-engine-rules.md](execution-engine-rules.md) | Exit-engine semantics: stop ratchet, relative author updates, edge cases          |

Related artifacts in the repo root:

- `Execution Step Explorations.html` — design canvas with the three layout variations (B · Numbered flow was chosen and wired in)
- `Execution Adaptivity Decision Tree.html` — visual version of the adaptivity decision tree
- `ExecutionView.jsx` / `execution.css` — the live implementation
- `RiskView.jsx` — the superseded pre-redesign step (kept for reference, no longer loaded)
