from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.deletion import DeletedSignalEvidence
from verasig.domain.event import RawSignalEvent
from verasig.domain.market_ports import MarketData
from verasig.domain.message import RawTelegramMessage
from verasig.domain.risk_config import RiskConfig
from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal
from verasig.domain.simulation import SimOutcome, SimOutcomeKind
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.provider_scores.scorecard import build_provider_score
from verasig.features.risk.policy import RiskConfigPolicy
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.extract_service import ExtractService
from verasig.features.signals.fold import fold
from verasig.features.simulation import repository as backtest_repository
from verasig.features.simulation.simulator import simulate_outcomes_from_market_data


@dataclass(frozen=True)
class BacktestInputs:
    channel: object
    messages: list[RawTelegramMessage]
    message_count: int
    events: list[RawSignalEvent]
    signals: list[ExtractedSignal]
    unrecognized: list[UnrecognizedSignal]
    deletions: list[DeletedSignalEvidence]
    folded_signals: list


@dataclass(frozen=True)
class BacktestSummary:
    score: int
    win_rate: float
    pnl: float
    outcomes: list[SimOutcome]


def run_backtest(
    session_factory: sessionmaker,
    user_id: UUID,
    channel_id: int,
    market_data: MarketData,
    risk_config: RiskConfig,
    now: datetime,
) -> BacktestSummary:
    inputs = load_folded_signals(session_factory, user_id, channel_id)
    outcomes = simulate_outcomes(inputs, market_data, risk_config, now)
    summary = compose_score(inputs, outcomes, now)
    persist_result(session_factory, user_id, channel_id, summary, now)
    return summary


def load_folded_signals(
    session_factory: sessionmaker, user_id: UUID, channel_id: int
) -> BacktestInputs:
    with session_factory() as session:
        _materialize_missing_outcomes(session, user_id, channel_id)
        session.commit()
        channel = feed_repository.read_feed_channel(session, user_id, channel_id)
        messages = message_repository.read_messages(session, user_id, channel_id)
        events = event_repository.read_signal_events(session, user_id, channel_id)
        signals = outcome_repository.read_extracted_signals(
            session, channel_id, user_id
        )
        unrecognized = outcome_repository.read_unrecognized_signals(
            session, channel_id, user_id
        )
        deletions = deletion_repository.read_deletion_evidence(
            session, user_id, channel_id
        )
        message_count = message_repository.count_messages(session, user_id, channel_id)
    return BacktestInputs(
        channel=channel,
        messages=messages,
        message_count=message_count,
        events=events,
        signals=signals,
        unrecognized=unrecognized,
        deletions=deletions,
        folded_signals=fold(signals, events, messages),
    )


def simulate_outcomes(
    inputs: BacktestInputs,
    market_data: MarketData,
    risk_config: RiskConfig,
    now: datetime,
) -> list[SimOutcome]:
    return simulate_outcomes_from_market_data(
        inputs.folded_signals,
        market_data,
        now,
        policy=RiskConfigPolicy(risk_config),
    )


def compose_score(
    inputs: BacktestInputs, outcomes: list[SimOutcome], now: datetime
) -> BacktestSummary:
    score, _explanation = build_provider_score(
        channel=inputs.channel,
        messages=inputs.messages,
        message_count=inputs.message_count,
        events=inputs.events,
        signals=inputs.signals,
        unrecognized=inputs.unrecognized,
        deletions=inputs.deletions,
        sim_outcomes=outcomes,
        computed_at=now,
    )
    return BacktestSummary(
        score=round(score.score * 100),
        win_rate=_win_rate(outcomes),
        pnl=_compound_pnl(outcomes),
        outcomes=outcomes,
    )


def persist_result(
    session_factory: sessionmaker,
    user_id: UUID,
    channel_id: int,
    summary: BacktestSummary,
    now: datetime,
) -> None:
    with session_factory() as session:
        backtest_repository.insert_result(
            session,
            user_id,
            channel_id,
            summary.score,
            Decimal(str(summary.win_rate)),
            Decimal(str(summary.pnl)),
            [_outcome_json(outcome) for outcome in summary.outcomes],
            now,
        )
        feed_repository.set_status(session, user_id, channel_id, "analyzed")
        session.commit()


def _materialize_missing_outcomes(session, user_id: UUID, channel_id: int) -> None:
    events = event_repository.read_signal_events(session, user_id, channel_id)
    done_event_ids = {
        outcome.event_id
        for outcome in [
            *outcome_repository.read_extracted_signals(session, channel_id, user_id),
            *outcome_repository.read_unrecognized_signals(session, channel_id, user_id),
        ]
    }
    service = ExtractService(
        rule_repository.read_parser_rules(session, channel_id, user_id)
    )
    for event in events:
        if event.id in done_event_ids:
            continue
        outcome_repository.record_outcome(session, service.extract(event), user_id)


def _tested_outcomes(outcomes: list[SimOutcome]) -> list[SimOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.kind is not SimOutcomeKind.UNFILLED
        and outcome.pct_return is not None
    ]


def _win_rate(outcomes: list[SimOutcome]) -> float:
    tested = _tested_outcomes(outcomes)
    if not tested:
        return 0.0
    wins = sum(1 for outcome in tested if outcome.pct_return and outcome.pct_return > 0)
    return round(wins / len(tested) * 100, 1)


def _compound_pnl(outcomes: list[SimOutcome]) -> float:
    growth = Decimal(1)
    for outcome in _tested_outcomes(outcomes):
        growth *= Decimal(1) + Decimal(str(outcome.pct_return)) / Decimal(100)
    return float((growth - Decimal(1)) * Decimal(100))


def _outcome_json(outcome: SimOutcome) -> dict:
    return {
        "rootSignalId": str(outcome.folded_signal_id),
        "kind": outcome.kind.value,
        "rMultiple": outcome.r_multiple,
        "pctReturn": outcome.pct_return,
        "exitReason": outcome.exit_reason,
    }
