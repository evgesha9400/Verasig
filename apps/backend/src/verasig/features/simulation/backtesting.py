from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.deletion import DeletedSignalEvidence
from verasig.domain.feed import FeedStatus
from verasig.domain.market_ports import MarketData
from verasig.domain.message import RawTelegramMessage
from verasig.domain.risk_config import RiskConfig
from verasig.domain.signal import Signal
from verasig.domain.simulation import SimOutcome, SimOutcomeKind
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.provider_scores.scorecard import build_provider_score
from verasig.features.risk.policy import RiskConfigPolicy
from verasig.features.signals import (
    lifecycle_link_repository,
    outcome_repository,
)
from verasig.features.signals.fold import fold
from verasig.features.simulation import repository as backtest_repository
from verasig.features.simulation.simulator import simulate_outcomes_from_market_data


@dataclass(frozen=True)
class BacktestInputs:
    channel: object
    messages: list[RawTelegramMessage]
    message_count: int
    signals: list[Signal]
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
        channel = feed_repository.read_feed_channel(session, user_id, channel_id)
        messages = message_repository.read_messages(session, user_id, channel_id)
        signals = outcome_repository.read_signals(session, channel_id, user_id)
        deletions = deletion_repository.read_deletion_evidence(
            session, user_id, channel_id
        )
        message_count = message_repository.count_messages(session, user_id, channel_id)
        # manual lifecycle links let the fold attach modifiers to a root signal;
        # the backtest fold must honour them exactly as the signals view does.
        manual_links = {
            link.external_message_id: link.root_signal_id
            for link in lifecycle_link_repository.read_links(
                session, user_id, channel_id
            )
        }
    return BacktestInputs(
        channel=channel,
        messages=messages,
        message_count=message_count,
        signals=signals,
        deletions=deletions,
        folded_signals=fold(signals, messages, manual_links=manual_links),
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
    # Every signal is an extraction now (no stored "misses"), so the score's
    # candidate-event input is exactly the signal set, and nothing is missed.
    score, _explanation = build_provider_score(
        channel=inputs.channel,
        messages=inputs.messages,
        message_count=inputs.message_count,
        events=inputs.signals,
        signals=inputs.signals,
        missed_event_ids=[],
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
        feed_repository.set_status(session, user_id, channel_id, FeedStatus.ANALYZED)
        session.commit()


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
