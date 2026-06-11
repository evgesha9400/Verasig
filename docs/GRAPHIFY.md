# Graphify Protocol

## Purpose

- Keep a queryable project knowledge graph in `graphify-out/`.
- Use the graph before architecture, refactor, onboarding, and broad codebase questions.
- Treat `graphify-out/graph.json` as the canonical graph output.
- Treat `graphify-out/GRAPH_REPORT.md` as the audit report.
- Treat `graphify-out/graph.html` as the browser view.

## Default Rule

- Use update by default.
- Use full recursive rebuild when project meaning or structure changes.
- Use cluster-only when graph data is current but communities look wrong.

## When To Run

| Trigger | Command |
|---|---|
| Daily active development | `$graphify . --update` |
| Code-only change | `$graphify . --update` |
| Docs, ADRs, requirements, or mockups changed | `$graphify . --update` |
| Feature branch merged | `$graphify . --update` |
| Before architecture work | `$graphify . --update` |
| Before onboarding an agent or person | `$graphify . --update` |
| Folder/module boundaries changed | Full recursive rebuild |
| Major refactor completed | Full recursive rebuild |
| Milestone or sprint end | Full recursive rebuild |
| Graph feels noisy or stale | Full recursive rebuild |
| Communities feel wrong but files are current | `$graphify . --cluster-only` |

## Copy-Paste Commands

- Paste `$graphify` commands into the agent chat.
- Run terminal commands only when explicitly marked terminal.

### Default Update

```text
$graphify . --update
```

### Full Root Build

```text
$graphify .
```

### Full Recursive Rebuild

```text
$graphify . recursively from the deepest level that fits the 200-file guard, then merge all slices into root graphify-out
```

### Current Recursive Slices Reference

```text
$graphify apps/backend
$graphify apps/frontend
$graphify docs
$graphify libs
```

- Prefer the full recursive rebuild command for root merge.
- Include root project docs in the final root merge.

### Recluster Existing Graph

```text
$graphify . --cluster-only
```

### Query The Graph

```text
$graphify query "Why does RawTelegramMessage connect extraction, distillation, deletion, ingestion, scoring, and lifecycle?"
```

### Trace A Specific Path

```text
$graphify path "RawTelegramMessage" "ProviderScore"
```

### Explain A Node

```text
$graphify explain "RawTelegramMessage"
```

## Recursive Rebuild Rules

- Start at the repository root.
- Detect supported files.
- If the root corpus is over `200` files, split by top-level folders.
- Keep splitting until each slice is at or under `200` supported files.
- Run extraction per fitted slice.
- Merge extracted nodes and edges into the root graph.
- Generate final root outputs only in `graphify-out/`.
- Keep the root graph as the source of truth.

## Current Slice Map

| Slice | Purpose |
|---|---|
| `apps/backend` | Backend service, migrations, CLI, tests |
| `apps/frontend` | React UI, design system, frontend assets |
| `docs` | Product docs, ADRs, work specs, business docs |
| `libs` | Shared contract documentation |
| Root docs | README and compose-level project metadata |

## Before Broad Questions

- Query `graphify-out/graph.json` first.
- Use graph traversal before broad `rg` or multi-file reads.
- Use `query` for broad neighborhood context.
- Use `path` for dependency chains.
- Use `explain` for a single concept.

## After Running

- Open `graphify-out/graph.html` for visual navigation.
- Read `graphify-out/GRAPH_REPORT.md` for audit findings.
- Use `graphify-out/graph.json` for future graph queries.
- Review `God Nodes` for core abstractions.
- Review `Surprising Connections` for cross-boundary risks.
- Review `Suggested Questions` for follow-up investigation.

## Optional Automation

Terminal:

```text
graphify hook install
graphify hook status
graphify hook uninstall
```

```text
$graphify . --watch
```

## Maintenance Rule

- Update after small changes.
- Rebuild after structural changes.
- Recluster after grouping changes.
- Query before guessing.
