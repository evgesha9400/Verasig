# Graph Report - .  (2026-06-11)

## Corpus Check
- 236 files · ~81,700 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1879 nodes · 7093 edges · 115 communities (95 shown, 20 thin omitted)
- Extraction: 47% EXTRACTED · 53% INFERRED · 0% AMBIGUOUS · INFERRED: 3744 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Extraction Outcomes Backend|Extraction Outcomes Backend]]
- [[_COMMUNITY_Extraction Outcomes Backend|Extraction Outcomes Backend]]
- [[_COMMUNITY_Extraction Outcomes Backend|Extraction Outcomes Backend]]
- [[_COMMUNITY_Extraction Outcomes Backend|Extraction Outcomes Backend]]
- [[_COMMUNITY_Rule Distillation Backend|Rule Distillation Backend]]
- [[_COMMUNITY_Rule Distillation Backend|Rule Distillation Backend]]
- [[_COMMUNITY_Backend Service Lifecycle|Backend Service Lifecycle]]
- [[_COMMUNITY_Backend Service Candidate|Backend Service Candidate]]
- [[_COMMUNITY_Deletion Evidence Backend|Deletion Evidence Backend]]
- [[_COMMUNITY_Backend Service Source|Backend Service Source]]
- [[_COMMUNITY_Rule Distillation Backend|Rule Distillation Backend]]
- [[_COMMUNITY_Deletion Evidence Telegram|Deletion Evidence Telegram]]
- [[_COMMUNITY_Design System Jsx|Design System Jsx]]
- [[_COMMUNITY_Rule Distillation Distiller|Rule Distillation Distiller]]
- [[_COMMUNITY_Backend Service Channel|Backend Service Channel]]
- [[_COMMUNITY_Backend Service Session|Backend Service Session]]
- [[_COMMUNITY_Rule Distillation Backend|Rule Distillation Backend]]
- [[_COMMUNITY_Backend Service Reference|Backend Service Reference]]
- [[_COMMUNITY_Frontend UI Package|Frontend UI Package]]
- [[_COMMUNITY_Frontend UI Jsx|Frontend UI Jsx]]
- [[_COMMUNITY_Business Model Docs|Business Model Docs]]
- [[_COMMUNITY_Backend Service Llm|Backend Service Llm]]
- [[_COMMUNITY_Backend Service Live|Backend Service Live]]
- [[_COMMUNITY_Design System Contract|Design System Contract]]
- [[_COMMUNITY_Backend Service Telethon|Backend Service Telethon]]
- [[_COMMUNITY_Backend Service Signal|Backend Service Signal]]
- [[_COMMUNITY_Frontend UI Readme|Frontend UI Readme]]
- [[_COMMUNITY_Rule Distillation Docs|Rule Distillation Docs]]
- [[_COMMUNITY_Backend Service Fold|Backend Service Fold]]
- [[_COMMUNITY_Rule Distillation Docs|Rule Distillation Docs]]
- [[_COMMUNITY_Provider Scoring Work|Provider Scoring Work]]
- [[_COMMUNITY_Deletion Evidence Docs|Deletion Evidence Docs]]
- [[_COMMUNITY_Backend Service Live|Backend Service Live]]
- [[_COMMUNITY_Extraction Outcomes Docs|Extraction Outcomes Docs]]
- [[_COMMUNITY_Design System Jsx|Design System Jsx]]
- [[_COMMUNITY_Frontend UI Bybit|Frontend UI Bybit]]
- [[_COMMUNITY_Backend Service Score|Backend Service Score]]
- [[_COMMUNITY_Provider Scoring Docs|Provider Scoring Docs]]
- [[_COMMUNITY_Backend Service Candidate|Backend Service Candidate]]
- [[_COMMUNITY_Backend Service Integration|Backend Service Integration]]
- [[_COMMUNITY_Deletion Evidence Deletions|Deletion Evidence Deletions]]
- [[_COMMUNITY_Provider Scoring Design|Provider Scoring Design]]
- [[_COMMUNITY_Backend Service Telegram|Backend Service Telegram]]
- [[_COMMUNITY_Backend Service Recall|Backend Service Recall]]
- [[_COMMUNITY_Observer Workflow Docs|Observer Workflow Docs]]
- [[_COMMUNITY_Observer Workflow Docs|Observer Workflow Docs]]
- [[_COMMUNITY_Design System Jsx|Design System Jsx]]
- [[_COMMUNITY_Design System Jsx|Design System Jsx]]
- [[_COMMUNITY_Extraction Outcomes Docs|Extraction Outcomes Docs]]
- [[_COMMUNITY_Observer Workflow Work|Observer Workflow Work]]
- [[_COMMUNITY_Business Model Milestone|Business Model Milestone]]
- [[_COMMUNITY_Deletion Evidence Raw|Deletion Evidence Raw]]
- [[_COMMUNITY_Backend Service Stats|Backend Service Stats]]
- [[_COMMUNITY_Backend Service Bybit|Backend Service Bybit]]
- [[_COMMUNITY_Business Model Docs|Business Model Docs]]
- [[_COMMUNITY_Backend Service Lifecycle|Backend Service Lifecycle]]
- [[_COMMUNITY_Observer Workflow Docs|Observer Workflow Docs]]
- [[_COMMUNITY_Architecture Decisions Policy|Architecture Decisions Policy]]
- [[_COMMUNITY_Backend Service Static|Backend Service Static]]
- [[_COMMUNITY_Frontend UI Pipeline|Frontend UI Pipeline]]
- [[_COMMUNITY_Backend Service Message|Backend Service Message]]
- [[_COMMUNITY_Backend Service Channel|Backend Service Channel]]
- [[_COMMUNITY_Design System Jsx|Design System Jsx]]
- [[_COMMUNITY_Frontend UI Verasig|Frontend UI Verasig]]
- [[_COMMUNITY_Backend Service Apps|Backend Service Apps]]
- [[_COMMUNITY_Backend Service Trade|Backend Service Trade]]
- [[_COMMUNITY_Frontend UI Login|Frontend UI Login]]
- [[_COMMUNITY_Frontend UI Verify|Frontend UI Verify]]
- [[_COMMUNITY_Frontend UI Backtest|Frontend UI Backtest]]
- [[_COMMUNITY_Frontend UI Label|Frontend UI Label]]
- [[_COMMUNITY_Observer Workflow Layer|Observer Workflow Layer]]
- [[_COMMUNITY_Backend Service Filter|Backend Service Filter]]
- [[_COMMUNITY_Backend Service Parser|Backend Service Parser]]
- [[_COMMUNITY_Backend Service Apps|Backend Service Apps]]
- [[_COMMUNITY_Design System Select|Design System Select]]
- [[_COMMUNITY_Design System Tabs|Design System Tabs]]
- [[_COMMUNITY_Design System Toast|Design System Toast]]
- [[_COMMUNITY_Design System Banner|Design System Banner]]
- [[_COMMUNITY_Design System Avatar|Design System Avatar]]
- [[_COMMUNITY_Design System Badge|Design System Badge]]
- [[_COMMUNITY_Design System Icon|Design System Icon]]
- [[_COMMUNITY_Design System Tag|Design System Tag]]
- [[_COMMUNITY_Design System Tooltip|Design System Tooltip]]
- [[_COMMUNITY_Design System Button|Design System Button]]
- [[_COMMUNITY_Design System Banner|Design System Banner]]
- [[_COMMUNITY_Design System Dialog|Design System Dialog]]
- [[_COMMUNITY_Design System Checkbox|Design System Checkbox]]
- [[_COMMUNITY_Design System Input|Design System Input]]
- [[_COMMUNITY_Design System Switch|Design System Switch]]

## God Nodes (most connected - your core abstractions)
1. `RawTelegramMessage` - 266 edges
2. `RawSignalEvent` - 171 edges
3. `TelegramChannel` - 160 edges
4. `ExtractedSignal` - 144 edges
5. `DeletedSignalEvidence` - 132 edges
6. `DeletionConfidence` - 123 edges
7. `SimOutcome` - 121 edges
8. `FoldedSignal` - 100 edges
9. `MaterializationPath` - 99 edges
10. `Side` - 96 edges

## Surprising Connections (you probably didn't know these)
- `Shared DTOs And JSON Contracts` --semantically_similar_to--> `Canonical Pydantic Contracts`  [INFERRED] [semantically similar]
  libs/contracts/README.md → docs/work/observer/data-contracts.md
- `test_fake_exchange_satisfies_protocol_and_honours_injected_symbols()` --calls--> `FakeExchange`  [INFERRED]
  backend/tests/unit/test_exchange.py → backend/tests/fakes.py
- `test_fake_extractor_returns_canned_intent_and_counts_calls()` --calls--> `FakeExtractor`  [INFERRED]
  backend/tests/unit/test_llm_fallback.py → backend/tests/fakes.py
- `TelegramChannel` --uses--> `TelegramChannel`  [INFERRED]
  backend/tests/unit/test_cli_telegram.py → backend/src/verasig/domain/channel.py
- `test_claude_cli_extractor_satisfies_protocol()` --calls--> `ClaudeCliExtractor`  [INFERRED]
  backend/tests/unit/test_llm_fallback.py → backend/src/verasig/services/extraction/llm_fallback.py

## Hyperedges (group relationships)
- **Backend Runtime Stack** — dockercompose_backend_app_container, dockercompose_postgres_database, readme_root_environment_contract, backendreadme_alembic_migrations [EXTRACTED 1.00]
- **Trade Signal Extraction Contract** — distillpilot_filter_rule, distillpilot_parser_rules, distillpilot_trade_signal_field_map, extractpilot_single_trade_extraction, extractmiss_non_tradable_message [INFERRED 0.88]
- **Verification UI State System** — domain_verification_state_taxonomy, core_badge, feedback_banner, feedback_toast, core_avatar [EXTRACTED 1.00]
- **Human Assisted Rule Distillation Loop** — adr0002_operator_labeling, adr0001_golden_label, adr0002_golden_corpus, adr0002_llm_rule_distillation, adr0005_filter_rule, adr0002_parser_rule, adr0005_filter_drift_warning, adr0002_parser_drift_warning [EXTRACTED 1.00]
- **Proof First Evidence Chain** — adr0001_raw_telegram_message, adr0001_raw_signal_event, adr0006_trade_intent, adr0006_extracted_signal, adr0008_deleted_signal_evidence, adr0009_provider_score_explanation, adr0009_provider_score [INFERRED 0.86]
- **Storage Placement Taxonomy** — adr0001_raw_telegram_message, adr0006_extracted_signal, adr0007_folded_signal, adr0008_deleted_signal_evidence, adr0009_provider_score [EXTRACTED 1.00]
- **Observer Evidence Pipeline** — context_rawtelegrammessage, context_rawsignalevent, context_extractedsignal, context_foldedsignal, context_simulated_outcome, context_providerscore, context_providerscoreexplanation [EXTRACTED 1.00]
- **Source Labeling Workflow** — requirements_sources_page, requirements_telegram_setup, requirements_channel_list, requirements_backfill_progress, requirements_label_distill_verify_loop, requirements_extraction_after_verification, requirements_destination_setup, requirements_risk_policy, requirements_analysis_provider_score [EXTRACTED 1.00]
- **Labeling UI Variants** — a_focus_deck_labeling_mockup, b_refined_ledger_labeling_mockup, c_reading_stream_labeling_mockup [EXTRACTED 1.00]
- **Verasig Mark Visual Form** — verasig_mark_brand_mark, verasig_mark_angular_signal_stroke, verasig_mark_terminal_dot, verasig_mark_current_color_theming [EXTRACTED 1.00]

## Communities (115 total, 20 thin omitted)

### Community 0 - "Extraction Outcomes Backend"
Cohesion: 0.05
Nodes (197): datetime, ExtractedSignal, LlmExtractor, ParserRule, TradeIntent, UnrecognizedSignal, bool, DeletedSignalEvidence (+189 more)

### Community 1 - "Extraction Outcomes Backend"
Cohesion: 0.05
Nodes (138): datetime, str, EntryType, ParserRule, TradeIntent, bool, Decimal, ExtractedSignal (+130 more)

### Community 2 - "Extraction Outcomes Backend"
Cohesion: 0.06
Nodes (135): bool, datetime, DeletedSignalEvidence, ExtractedSignal, ExtractOutcome, FoldedSignal, FoldStep, int (+127 more)

### Community 3 - "Extraction Outcomes Backend"
Cohesion: 0.06
Nodes (87): DeletedSignalEvidence, int, Session, FilterDriftWarning, int, ParserDriftWarning, Session, str (+79 more)

### Community 4 - "Rule Distillation Backend"
Cohesion: 0.07
Nodes (65): int, RawTelegramMessage, sessionmaker, str, TelegramSource, datetime, DeletedSignalEvidence, int (+57 more)

### Community 5 - "Rule Distillation Backend"
Cohesion: 0.09
Nodes (36): bool, datetime, FilterRule, FoldedSignal, GoldenLabel, int, Kline, ParserRule (+28 more)

### Community 6 - "Backend Service Lifecycle"
Cohesion: 0.08
Nodes (46): Decimal, str, bool, Decimal, str, Decimal, str, _all() (+38 more)

### Community 7 - "Backend Service Candidate"
Cohesion: 0.09
Nodes (36): datetime, bool, Exchange, RawSignalEvent, RawTelegramMessage, str, bool, datetime (+28 more)

### Community 8 - "Deletion Evidence Backend"
Cohesion: 0.13
Nodes (33): datetime, DeletedSignalEvidence, int, RawTelegramMessage, DeletedSignalEvidence, int, sessionmaker, str (+25 more)

### Community 9 - "Backend Service Source"
Cohesion: 0.11
Nodes (17): int, str, _dialog(), _entity(), FakeTelethonClient, FakeTelethonMessage, _full_chat(), _instant() (+9 more)

### Community 10 - "Rule Distillation Backend"
Cohesion: 0.21
Nodes (31): datetime, bool, Exchange, FilterDriftWarning, FilterRule, int, ParserRule, RawSignalEvent (+23 more)

### Community 11 - "Deletion Evidence Telegram"
Cohesion: 0.22
Nodes (28): bool, DeliveryMode, TelegramChannel, TelegramLiveEvent, bool, DeletedSignalEvidence, int, sessionmaker (+20 more)

### Community 12 - "Design System Jsx"
Cohesion: 0.08
Nodes (18): Avatar(), s, TONE, s, s, s, Tag(), expected (+10 more)

### Community 13 - "Rule Distillation Distiller"
Cohesion: 0.17
Nodes (23): FilterRule, GoldenLabel, int, ParserRule, str, GoldenLabel, ClaudeCliDistiller, _content() (+15 more)

### Community 14 - "Backend Service Channel"
Cohesion: 0.20
Nodes (23): ChannelReference, datetime, float, str, TelegramClient, ChannelReference, int, Session (+15 more)

### Community 15 - "Backend Service Session"
Cohesion: 0.16
Nodes (26): int, Settings, str, TelegramClient, fetch_account(), format_account(), load_session_string(), make_client() (+18 more)

### Community 16 - "Rule Distillation Backend"
Cohesion: 0.16
Nodes (24): datetime, bool, FilterRule, float, GoldenLabel, int, ParserRule, RawTelegramMessage (+16 more)

### Community 17 - "Backend Service Reference"
Cohesion: 0.18
Nodes (21): bool, int, channel_lookup_handle(), _is_numeric_reference(), _is_telegram_link(), _is_title_reference(), _is_username_reference(), _link_handle() (+13 more)

### Community 18 - "Frontend UI Package"
Cohesion: 0.09
Nodes (22): dependencies, react, react-dom, devDependencies, eslint, eslint-plugin-react, eslint-plugin-react-hooks, jsdom (+14 more)

### Community 19 - "Frontend UI Jsx"
Cohesion: 0.11
Nodes (16): RegisterView(), ExchangesView(), Shell(), SettingsView(), SourcesView(), TelegramSetup(), App(), loadState() (+8 more)

### Community 20 - "Business Model Docs"
Cohesion: 0.11
Nodes (22): Conservative Compliance Copy, Platform Is End State Not MVP, Signal Is A First Class Dataset, InfraOps, PortfolioOps, Research Lab, StrategyOps, Unified GUI (+14 more)

### Community 21 - "Backend Service Llm"
Cohesion: 0.14
Nodes (17): str, TradeIntent, str, _content(), _extraction_prompt(), parse_extractor_output(), _subprocess_runner(), find_json_object() (+9 more)

### Community 22 - "Backend Service Live"
Cohesion: 0.25
Nodes (18): datetime, int, RawTelegramMessage, TelegramLiveEvent, ingest_live(), _median_latency(), _channel(), _deletion() (+10 more)

### Community 23 - "Design System Contract"
Cohesion: 0.17
Nodes (21): Avatar Component Contract, Badge Component Contract, Button Component Contract, IconButton Component Contract, Tabs Component Contract, Tag Component Contract, Core Component Showcase Card, Core Component Demo (+13 more)

### Community 24 - "Backend Service Telethon"
Cohesion: 0.24
Nodes (9): int, RawTelegramMessage, _advance_last_seen(), _deletion_channel_id(), _enqueue_deletion(), _json_safe(), _LiveEventState, _message_channel_id() (+1 more)

### Community 25 - "Backend Service Signal"
Cohesion: 0.13
Nodes (7): _signal(), test_extracted_signal_constructs_with_required_symbol_side_and_linkage(), test_extracted_signal_defaults_provenance_and_optionals(), test_extracted_signal_normalizes_symbol_via_inherited_validator(), test_extracted_signal_rejects_empty_symbol(), test_extracted_signal_rejects_missing_side(), test_extracted_signal_take_profits_are_ordered_decimals()

### Community 26 - "Frontend UI Readme"
Cohesion: 0.13
Nodes (18): Apps Workspace Boundaries, Backend Ownership Boundary, Contracts Ownership Boundary, Frontend Ownership Boundary, Runtime Environment Loading, Backend App Container, Postgres Database Service, Read-Only Secrets Mount (+10 more)

### Community 27 - "Rule Distillation Docs"
Cohesion: 0.16
Nodes (17): Focus Deck Labeling Mockup, Refined Ledger Labeling Mockup, Reading Stream Labeling Mockup, Candidate Filter, Distillation Loop, FilterDriftWarning, FilterRule, Golden Corpus (+9 more)

### Community 28 - "Backend Service Fold"
Cohesion: 0.40
Nodes (16): datetime, fold(), _at(), _entry(), _message(), test_chatter_reply_emits_no_phantom_step(), test_different_symbol_reply_that_is_a_signal_starts_its_own_root(), test_full_close_keyword_terminates_with_close_step_and_closed_at() (+8 more)

### Community 29 - "Rule Distillation Docs"
Cohesion: 0.21
Nodes (16): Candidate Filter, GoldenLabel, Golden Corpus, Human Assisted Rule Distillation Decision, LLM Rule Distillation, Operator Labeling, ParserDriftWarning, ParserRule (+8 more)

### Community 30 - "Provider Scoring Work"
Cohesion: 0.17
Nodes (16): DeletedSignalEvidence, MFE / MAE, ProviderScore, ProviderScoreExplanation, R-Multiple, Simulated Outcome, TelegramDeletionEvent, TelegramDeliveryEvent (+8 more)

### Community 31 - "Deletion Evidence Docs"
Cohesion: 0.16
Nodes (15): DeliveryMode, Hybrid Push Poll Live Ingestion Decision, TDLib Escape Hatch, TelegramLiveEvent, TelegramSource Protocol, Telethon Adapter, live_message_ids, Codebase Structure Boundary Decision (+7 more)

### Community 33 - "Backend Service Live"
Cohesion: 0.18
Nodes (9): int, str, TelegramChannel, TelegramDeliveryEvent, TelegramLiveEvent, _delivery(), FakeClient, FakeLiveSource (+1 more)

### Community 34 - "Extraction Outcomes Docs"
Cohesion: 0.15
Nodes (15): ExecutionPolicy, ExtractedSignal, FoldedSignal, ParserDriftWarning, Signal Lifecycle, SignalModification, UnrecognizedSignal, Recomputable Extraction Projection (+7 more)

### Community 35 - "Design System Jsx"
Cohesion: 0.32
Nodes (6): BrandPanel(), Badge(), Button(), Banner(), Input(), Icon()

### Community 36 - "Frontend UI Bybit"
Cohesion: 0.32
Nodes (10): datetime, int, Kline, str, Client, _from_millis(), _kline_params(), _parse_kline() (+2 more)

### Community 37 - "Backend Service Score"
Cohesion: 0.36
Nodes (13): int, _at(), _channel(), _event(), _id_gap(), _message(), _score_from_repo(), _seed_score_inputs() (+5 more)

### Community 38 - "Provider Scoring Docs"
Cohesion: 0.19
Nodes (13): FoldStep, FoldedSignal, Lifecycle Fold Recomputable Decision, lifecycle fold Function, SignalModification, ProviderScore, ProviderScore Recomputable Scorecard Decision, ProviderScoreExplanation (+5 more)

### Community 39 - "Backend Service Candidate"
Cohesion: 0.44
Nodes (11): datetime, derive_candidates(), _instant(), _seed(), test_derive_flags_signals_as_seed_heuristic_not_chatter(), test_derive_is_idempotent(), test_derive_uses_distilled_filter_rule_over_seed(), test_sweep_does_not_drift_on_existing_candidate() (+3 more)

### Community 40 - "Backend Service Integration"
Cohesion: 0.30
Nodes (10): datetime, int, RawTelegramMessage, TelegramChannel, _channel(), _instant(), _message(), test_advance_cursor_is_monotonic() (+2 more)

### Community 41 - "Deletion Evidence Deletions"
Cohesion: 0.38
Nodes (11): DeletedSignalEvidence, int, _channel(), _confirmed(), _evidence(), _suspected(), test_chatter_confirmed_deletion_is_hidden(), test_header_carries_channel_identity() (+3 more)

### Community 42 - "Provider Scoring Design"
Cohesion: 0.18
Nodes (11): Typed Evidence References, Provider Performance Dashboard Requirement, Data First Rule, Evidence Color Rule, No Fluid Type Rule, Rose Scarcity Rule, Score Evidence Table, Verasig Design System (+3 more)

### Community 43 - "Backend Service Telegram"
Cohesion: 0.22
Nodes (4): TelegramChannel, _channel(), test_format_stats_omits_handle_subs_and_marks_empty_cursor(), test_format_stats_renders_handle_cursor_and_subs()

### Community 44 - "Backend Service Recall"
Cohesion: 0.33
Nodes (7): GoldenLabel, _report(), test_corpus_has_a_meaningful_signal_denominator(), test_filter_recall_meets_quality_gate(), test_parser_precision_meets_quality_gate(), test_parser_recall_is_reported_not_gated(), FakeDistiller

### Community 45 - "Observer Workflow Docs"
Cohesion: 0.18
Nodes (11): TradeIntent, Shared DTOs And JSON Contracts, Canonical Pydantic Contracts, LlmExtractor Protocol, MarketData Protocol, Service Interfaces, Foundation Layer, Local Observer Stack (+3 more)

### Community 46 - "Observer Workflow Docs"
Cohesion: 0.18
Nodes (11): Active-User Proxy, Rescan, TelegramChannel, Backend Frontend Decoupling, Contracts Library, TelegramSource Protocol, Telegram Channel List, Coming Soon Sources And Destinations (+3 more)

### Community 47 - "Design System Jsx"
Cohesion: 0.24
Nodes (7): s, Switch(), ExecutionView(), VX_SAMPLE, vxFmt(), vxPlan(), VxPreview()

### Community 48 - "Design System Jsx"
Cohesion: 0.20
Nodes (7): s, Tabs(), s, Select(), hashId(), rawMessage(), SignalsView()

### Community 49 - "Extraction Outcomes Docs"
Cohesion: 0.31
Nodes (10): ExtractService, ExtractedSignal, extraction_method, Extraction Outcomes Shape And Lifecycle Decision, LlmExtractor, record_outcome, TradeIntent, UnrecognizedSignal (+2 more)

### Community 50 - "Observer Workflow Work"
Cohesion: 0.24
Nodes (10): RawSignalEvent, RawTelegramMessage, Append-Only Capture Tables, Work Item 0 Foundation Skeleton, Work Item 2 History Backfill, Observer Implementation Plan, Work Item 1 Telegram Session Login, Backfill Progress (+2 more)

### Community 51 - "Business Model Milestone"
Cohesion: 0.20
Nodes (10): Milestone C Cheap Cloud MVP, Milestone B Local MVP, Milestone A Operator Dogfood, Milestone E Paid Beta, Milestone D Pilot Interest, Milestone H Platform Scale, Milestone F Research Integration, Signal Lake (+2 more)

### Community 52 - "Deletion Evidence Raw"
Cohesion: 0.36
Nodes (9): RawSignalEvent, RawTelegramMessage, Two Layer Raw Capture Decision, DeletedSignalEvidence, Deletion Evidence Durable Projection Decision, Deletion Rescan, detect_deletions, Storage Taxonomy (+1 more)

### Community 54 - "Backend Service Stats"
Cohesion: 0.42
Nodes (7): datetime, _instant(), _message(), _populate(), test_stats_prints_capture_count_and_cursor(), test_stats_resolves_by_exact_title(), test_stats_resolves_by_numeric_id()

### Community 55 - "Backend Service Bybit"
Cohesion: 0.22
Nodes (8): result, category, list, symbol, retCode, retExtInfo, retMsg, time

### Community 56 - "Business Model Docs"
Cohesion: 0.25
Nodes (8): 3Commas, AI SRE Incumbents, Capitalise.ai, Competitive Gap, Cornix, QuantConnect, TradingView Webhooks, WunderTrading

### Community 57 - "Backend Service Lifecycle"
Cohesion: 0.46
Nodes (6): datetime, int, _at(), _message(), _seed_lifecycle(), test_lifecycle_cli_prints_folded_timeline()

### Community 59 - "Observer Workflow Docs"
Cohesion: 0.25
Nodes (8): Observer Design Spec, Operator Classification Evidence, Milestone G Live Execution, First Source Telegram, Observe-Only Exchange Mode, Signal Performance Operating System, Verasig, Web Dashboard

### Community 60 - "Architecture Decisions Policy"
Cohesion: 0.38
Nodes (7): Bybit Historical Klines, Conservative Observe Only Simulation Decision, ExecutionPolicy, ProviderStatedPolicy, R Multiple Outcome, Execution Lifecycle Future Compatible, Execution Outside MVP

### Community 61 - "Backend Service Static"
Cohesion: 0.33
Nodes (3): bool, str, normalize_base_symbol()

### Community 62 - "Frontend UI Pipeline"
Cohesion: 0.38
Nodes (5): Pipeline(), PIPELINE_PROCESS_STEPS, PIPELINE_STEPS, { container }, steps

### Community 63 - "Backend Service Message"
Cohesion: 0.43
Nodes (4): datetime, _instant(), test_raw_message_constructs_with_required_fields(), test_raw_message_defaults_optionals_to_none()

### Community 64 - "Backend Service Channel"
Cohesion: 0.60
Nodes (5): datetime, _instant(), test_channel_constructs_with_required_fields(), test_channel_defaults_optionals_to_none(), test_channel_rejects_missing_title()

### Community 65 - "Design System Jsx"
Cohesion: 0.33
Nodes (3): IconButton(), s, ChatsView()

### Community 66 - "Frontend UI Verasig"
Cohesion: 0.47
Nodes (6): Angular Signal Stroke, Verasig Mark, CurrentColor Theming, Verasig Product Identity, verasig-mark.svg Asset, Terminal Dot

### Community 67 - "Backend Service Apps"
Cohesion: 0.40
Nodes (5): Alembic Migrations, Backend CLI Commands, Backend Layout, Backend Test Suite, Verasig Python Package Source

### Community 69 - "Backend Service Trade"
Cohesion: 0.67
Nodes (4): Distilled Trade Signal Parser Rules, LONG SHORT Side Aliases, Trade Signal Field Map, Single BTC LONG Trade Extraction

### Community 70 - "Frontend UI Login"
Cohesion: 0.50
Nodes (3): LoginView(), onLogin, onRegister

### Community 74 - "Observer Workflow Layer"
Cohesion: 0.50
Nodes (4): Contract Test Layer, Integration Test Layer, Observer TDD Test Plan, Unit Test Layer

### Community 82 - "Backend Service Apps"
Cohesion: 0.67
Nodes (3): Distilled Trade Signal Filter Rule, Recall and Field Precision Goal, Non-Tradable Message

## Knowledge Gaps
- **147 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+142 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RawTelegramMessage` connect `Rule Distillation Backend` to `Extraction Outcomes Backend`, `Extraction Outcomes Backend`, `Extraction Outcomes Backend`, `Extraction Outcomes Backend`, `Rule Distillation Backend`, `Backend Service Candidate`, `Deletion Evidence Backend`, `Backend Service Source`, `Rule Distillation Backend`, `Deletion Evidence Telegram`, `Rule Distillation Distiller`, `Backend Service Channel`, `Rule Distillation Backend`, `Backend Service Reference`, `Backend Service Live`, `Backend Service Telethon`, `Backend Service Fold`, `Backend Service Live`, `Backend Service Score`, `Backend Service Candidate`, `Backend Service Integration`, `Backend Service Recall`, `Backend Service Stats`, `Backend Service Lifecycle`, `Backend Service Message`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `Client` connect `Frontend UI Bybit` to `Extraction Outcomes Backend`, `Extraction Outcomes Backend`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `MarketData` connect `Extraction Outcomes Backend` to `Extraction Outcomes Backend`, `Extraction Outcomes Backend`, `Frontend UI Bybit`, `Rule Distillation Backend`, `Rule Distillation Backend`, `Rule Distillation Backend`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 264 inferred relationships involving `RawTelegramMessage` (e.g. with `FakeStreamInterrupted` and `FakeSource`) actually correct?**
  _`RawTelegramMessage` has 264 INFERRED edges - model-reasoned connections that need verification._
- **Are the 169 inferred relationships involving `RawSignalEvent` (e.g. with `RawSignalEvent` and `datetime`) actually correct?**
  _`RawSignalEvent` has 169 INFERRED edges - model-reasoned connections that need verification._
- **Are the 158 inferred relationships involving `TelegramChannel` (e.g. with `FakeStreamInterrupted` and `FakeSource`) actually correct?**
  _`TelegramChannel` has 158 INFERRED edges - model-reasoned connections that need verification._
- **Are the 142 inferred relationships involving `ExtractedSignal` (e.g. with `ExtractedSignal` and `datetime`) actually correct?**
  _`ExtractedSignal` has 142 INFERRED edges - model-reasoned connections that need verification._