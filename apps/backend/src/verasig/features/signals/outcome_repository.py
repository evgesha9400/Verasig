"""Signal repository functions.

Every persisted `signal` IS an extraction — the miner is the only source, and
Confirm replaces a feed's whole signal set as one atomic projection (delete +
insert; see `mining_confirm.confirm_mined_signals`), so there is no
upsert-by-message dance and no de-selected family can survive a smaller
reconfirm.
"""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.signal import Signal
from verasig.storage.models import SignalRow


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


def _signal_values(signal: Signal) -> dict:
    return {
        "id": signal.id,
        "external_id": signal.channel_id,
        "external_message_id": signal.message_id,
        "candidate_text": signal.candidate_text,
        "symbol": signal.symbol,
        "side": signal.side.value,
        "event_type": signal.event_type.value,
        "entry_type": signal.entry_type.value if signal.entry_type else None,
        "entry_low": signal.entry_low,
        "entry_high": signal.entry_high,
        "stop_loss": signal.stop_loss,
        "take_profits": _str_list(signal.take_profits),
        "leverage": signal.leverage,
        "confidence": signal.confidence,
        "rule_id": signal.rule_id,
        "extracted_at": signal.extracted_at,
        "created_at": signal.extracted_at,
    }


def _with_user_id(values: dict, user_id: UUID) -> dict:
    return {**values, "user_id": user_id}


def insert_signals(session: Session, signals: list[Signal], user_id: UUID) -> int:
    if not signals:
        return 0
    statement = (
        pg_insert(SignalRow)
        .values([_with_user_id(_signal_values(signal), user_id) for signal in signals])
        .on_conflict_do_nothing(
            index_elements=["user_id", "external_id", "external_message_id"]
        )
        .returning(SignalRow.id)
    )
    return len(session.execute(statement).fetchall())


def delete_signals_for_channel(
    session: Session, user_id: UUID, external_id: int
) -> None:
    """Clear a feed's whole signal projection before Confirm rewrites it — a
    de-selected family must not survive a smaller reconfirm (orphan bug)."""
    session.execute(
        delete(SignalRow).where(
            SignalRow.user_id == user_id,
            SignalRow.external_id == external_id,
        )
    )


def read_signal_channel(session: Session, user_id: UUID, signal_id: UUID) -> int | None:
    """The channel a signal belongs to, so a single signal can be projected
    against only its own feed instead of every feed the user owns."""
    return session.scalar(
        select(SignalRow.external_id).where(
            SignalRow.id == signal_id,
            SignalRow.user_id == user_id,
        )
    )


def read_signals(session: Session, channel_id: int, user_id: UUID) -> list[Signal]:
    rows = session.scalars(
        select(SignalRow).where(
            SignalRow.external_id == channel_id,
            SignalRow.user_id == user_id,
        )
    ).all()
    return [
        Signal(
            id=row.id,
            channel_id=row.external_id,
            message_id=row.external_message_id,
            candidate_text=row.candidate_text,
            symbol=row.symbol,
            side=row.side,
            event_type=row.event_type,
            entry_type=row.entry_type,
            entry_low=row.entry_low,
            entry_high=row.entry_high,
            stop_loss=row.stop_loss,
            take_profits=row.take_profits,
            leverage=row.leverage,
            confidence=row.confidence,
            rule_id=row.rule_id,
            extracted_at=row.extracted_at,
        )
        for row in rows
    ]


def read_confirmed_template_keys(
    session: Session, user_id: UUID, external_id: int
) -> list[str]:
    """Distinct template keys of this feed's persisted signals — the accepted
    families to reseed when a verified feed is reopened (rule_id == template_key)."""
    statement = (
        select(SignalRow.rule_id)
        .where(
            SignalRow.user_id == user_id,
            SignalRow.external_id == external_id,
            SignalRow.rule_id.is_not(None),
        )
        .distinct()
    )
    return list(session.scalars(statement).all())
