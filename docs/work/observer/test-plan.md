# Observer TDD Test Plan

Tests are the spec made executable. **Red → green → commit** for every step. Underlying implementation must be swappable without breaking tests (test behaviour through contracts, not internals).

## 1. Test layers

| Layer | Scope | Dependencies | Speed |
|---|---|---|---|
| **unit** | pure `domain/` + `services/` logic | none (fakes injected) | ms |
| **integration** | `storage/` repos + full pipeline | ephemeral Postgres (testcontainers) | seconds |
| **contract** | adapters satisfy their Protocol | recorded fixtures (CLI stdout, klines, msgs) | ms |

- **No test touches real Telegram, the real LLM CLI, the real Bybit API, or the network.**
- Real-adapter behaviour is pinned with **recorded fixtures** (canned stdout / JSON), not live calls.

## 2. Fixtures (the golden corpora)

```
tests/fixtures/
├── messages/<channel>.jsonl     # real captured RawTelegramMessage samples (anonymized)
├── labels/<channel>.jsonl       # operator GoldenLabel ground truth
├── cli/extract_*.txt            # canned Claude/Codex CLI stdout for FakeExtractor
├── cli/distill_*.txt            # canned CLI stdout for FakeDistiller
└── klines/<symbol>_<window>.json# canned Bybit klines for the simulator
```

- The labeled `messages/` + `labels/` pair is the **precision/recall oracle**.
- Fixtures are committed (anonymized); secrets never are.

## 3. Per-Work-Item Test Matrix

| work item | Key tests (behaviour) | Oracle / fixture | Acceptance metric |
|---|---|---|---|
| 0 Foundation | config loads from env; `health` connects DB; migrations apply | testcontainers PG | `health` OK; pytest green; ruff clean |
| 1 Session/login | session-string round-trip; missing session → fail-fast msg | fake session | `whoami` works after one `login` |
| 2 Backfill | persists N immutable rows w/ provenance; dedup `(channel,msg)`; no UPDATE | `messages/*.jsonl` via FakeSource | rows == accessible count; re-run +0 |
| 3 Candidate filter + distillation | seed: chatter→reject, signal-shaped→accept (recall-first, table-driven); FilterRule+ParserRule distilled from labels; rule-apply pure; planted miss→1 FilterDriftWarning; labels+rules persist | labeled msgs + FakeDistiller | filter recall ≥ 0.95 of labels; re-apply reproduces labels ≥ target |
| 4 Deterministic extract | symbol+side required; side normalization; entry MARKET/SINGLE/RANGE; TP list | labeled corpus | **precision ≥ 0.95**; recall reported |
| 5 LLM fallback + drift | fallback only on miss; **1 drift per fallback success**; real CLI never called | FakeExtractor + cli fixtures | drift count == fallback successes |
| 6 Lifecycle fold | entry+modify→effective SL updated at t; close terminates; standalone stays single; out-of-order | crafted threads | folds match expected timeline |
| 7 Deletion | present→absent ⇒ CONFIRMED w/ content; id-gap ⇒ SUSPECTED; contiguous ⇒ none | two snapshots | CONFIRMED retains original text |
| 8 Scorecard | each metric fn; weighted-normalized composite; every component has evidence_refs; re-weight changes score | computed inputs | 100% components traceable |
| 9 Simulation | market fill=next open; limit unfilled→UNFILLED; **same-candle tie→stop_first**; MFE/MAE; policy injectable | `klines/*.json` | known signal→expected R |
| 10 Live | push→row (`mode=PUSH`); delayed/absent push→poll catch-up **deduped** (arrives once); delete→CONFIRMED w/ ts | fake event stream + fake clock | median `captured_at − posted_at` ≤ poll interval |

## 4. Representative test specs (write these first, watch them fail)

**work item 4 — required fields + normalization (unit, pure):**
```python
@pytest.mark.parametrize("text,expected", [
    ("BTC long entry 65000 sl 64000 tp 67000",
     dict(symbol="BTCUSDT", side="LONG", entry_low=Decimal("65000"),
          stop_loss=Decimal("64000"), take_profits=[Decimal("67000")])),
    ("ETH sell market",                       # no entry price → MARKET, no SL/TP
     dict(symbol="ETHUSDT", side="SHORT", entry_type="MARKET")),
    ("gm everyone",                            # not a signal
     None),                                    # → UnrecognizedSignal upstream
])
def test_deterministic_parse(rule, text, expected):
    result = parse(rule, RawSignalEvent(candidate_text=text, ...))
    assert _matches(result, expected)
```

**work item 5 — drift coverage invariant (unit, fake fallback):**
```python
def test_fallback_success_emits_exactly_one_drift():
    svc = ExtractService(rules=[], fallback=FakeExtractor(returns=SOME_SIGNAL))
    out = svc.extract(event)                   # rules empty ⇒ deterministic miss
    assert isinstance(out.signal, ExtractedSignal)
    assert len(out.drift_warnings) == 1
    assert out.signal.extraction_method == "LLM_FALLBACK"

def test_fallback_not_called_when_deterministic_matches():
    fb = FakeExtractor(); svc = ExtractService(rules=[GOOD_RULE], fallback=fb)
    svc.extract(matching_event)
    assert fb.calls == 0                        # cost guard
```

**work item 9 — conservative tie-break (unit, canned klines):**
```python
def test_same_candle_stop_and_tp_resolves_stop_first():
    signal = folded(side="LONG", entry=100, stop=95, tps=[110])
    klines = [bar(low=94, high=111)]            # spans both
    out = ProviderStatedPolicy().simulate(signal, klines)
    assert out.exit_reason == "stop"
    assert out.r_multiple == pytest.approx(-1.0)
```

**work item 2 — append-only / idempotent (integration, PG):**
```python
def test_backfill_is_idempotent(pg_session, fake_source):
    backfill(fake_source, channel_id=1, session=pg_session)
    n1 = count(RawTelegramMessage)
    backfill(fake_source, channel_id=1, session=pg_session)   # re-run
    assert count(RawTelegramMessage) == n1                    # no dupes
```

## 5. Precision / recall harness (cross-cutting)

- A single `evaluate(channel)` test loads `labels/<channel>.jsonl`, runs the full extract pipeline over `messages/<channel>.jsonl`, and asserts:
  - `precision >= 0.95` (quality gate).
  - `recall` is **computed and reported** (not gated below target; reported for larger-corpus validation).
  - **filter recall `>= 0.95`** measured on `GoldenLabel.is_signal` — the candidate gate is advisory, so the denominator is `GoldenLabel`, **not** the candidate subset ([ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md)).
- Output: a small table (TP/FP/FN per field) written to test logs — feeds the scorecard's parser-confidence component.

## 6. Definition of Done

- [ ] Failing test written first, observed failing.
- [ ] Minimal implementation; test green.
- [ ] `ruff format` + `ruff check` clean; imports sorted.
- [ ] No real network/CLI/Telegram in tests.
- [ ] Conventional commit per work item.
