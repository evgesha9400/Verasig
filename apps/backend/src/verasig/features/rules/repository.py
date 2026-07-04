"""Rule repository functions.

Domain rules/labels speak `channel_id`/`message_id`; storage speaks
`external_id`/`external_message_id` and is user-owned, so reads/writes translate.
"""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.parser_rule import ParserRule
from verasig.storage.models import (
    FilterRuleRow,
    GoldenLabelRow,
    ParserRuleRow,
)


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


def upsert_filter_rule(session: Session, rule: FilterRule) -> None:
    statement = pg_insert(FilterRuleRow).values(
        rule_id=rule.rule_id,
        user_id=rule.user_id,
        external_id=rule.channel_id,
        version=rule.version,
        include_patterns=rule.include_patterns,
        exclude_patterns=rule.exclude_patterns,
        matched_reason_template=rule.matched_reason_template,
        recall_target=rule.recall_target,
        python_filter=rule.python_filter,
        display=rule.display,
        created_at=rule.created_at,
        distilled_from_label_ids=_str_list(rule.distilled_from_label_ids),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[FilterRuleRow.rule_id],
        set_={
            "external_id": statement.excluded.external_id,
            "version": statement.excluded.version,
            "include_patterns": statement.excluded.include_patterns,
            "exclude_patterns": statement.excluded.exclude_patterns,
            "matched_reason_template": statement.excluded.matched_reason_template,
            "recall_target": statement.excluded.recall_target,
            "python_filter": statement.excluded.python_filter,
            "display": statement.excluded.display,
            "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
        },
    )
    session.execute(statement)


def read_filter_rules(
    session: Session, channel_id: int, user_id: UUID
) -> list[FilterRule]:
    rows = session.scalars(
        select(FilterRuleRow).where(
            FilterRuleRow.external_id == channel_id,
            FilterRuleRow.user_id == user_id,
        )
    ).all()
    return [
        FilterRule(
            rule_id=row.rule_id,
            user_id=row.user_id,
            channel_id=row.external_id,
            version=row.version,
            include_patterns=row.include_patterns,
            exclude_patterns=row.exclude_patterns,
            matched_reason_template=row.matched_reason_template,
            recall_target=row.recall_target,
            python_filter=row.python_filter,
            display=row.display,
            created_at=row.created_at,
            distilled_from_label_ids=row.distilled_from_label_ids,
        )
        for row in rows
    ]


def read_rule_feed_ids(
    session: Session, user_id: UUID, channel_ids: list[int]
) -> set[int]:
    if not channel_ids:
        return set()
    filter_ids = session.scalars(
        select(FilterRuleRow.external_id).where(
            FilterRuleRow.user_id == user_id,
            FilterRuleRow.external_id.in_(channel_ids),
        )
    ).all()
    parser_ids = session.scalars(
        select(ParserRuleRow.external_id).where(
            ParserRuleRow.user_id == user_id,
            ParserRuleRow.external_id.in_(channel_ids),
        )
    ).all()
    return {
        channel_id
        for channel_id in [*filter_ids, *parser_ids]
        if channel_id is not None
    }


def next_rule_version(session: Session, user_id: UUID, channel_id: int) -> int:
    """One past the highest version across both rule tables for this feed.

    Mining Confirm replaces a feed's rules by bumping the version and deleting
    the prior rows, so no stale version can shadow the re-mined ruleset.
    """
    filter_max = session.scalar(
        select(func.max(FilterRuleRow.version)).where(
            FilterRuleRow.user_id == user_id, FilterRuleRow.external_id == channel_id
        )
    )
    parser_max = session.scalar(
        select(func.max(ParserRuleRow.version)).where(
            ParserRuleRow.user_id == user_id, ParserRuleRow.external_id == channel_id
        )
    )
    return max(filter_max or 0, parser_max or 0) + 1


def delete_feed_rules(
    session: Session, user_id: UUID, channel_id: int
) -> tuple[int, int]:
    """Remove all of a feed's filter + parser rules; returns (filters, parsers)."""
    filters = session.execute(
        delete(FilterRuleRow).where(
            FilterRuleRow.user_id == user_id, FilterRuleRow.external_id == channel_id
        )
    ).rowcount
    parsers = session.execute(
        delete(ParserRuleRow).where(
            ParserRuleRow.user_id == user_id, ParserRuleRow.external_id == channel_id
        )
    ).rowcount
    return filters, parsers


def upsert_parser_rules(session: Session, rules: list[ParserRule]) -> None:
    for rule in rules:
        statement = pg_insert(ParserRuleRow).values(
            rule_id=rule.rule_id,
            user_id=rule.user_id,
            external_id=rule.channel_id,
            version=rule.version,
            patterns=rule.patterns,
            field_map=rule.field_map,
            side_aliases={key: side.value for key, side in rule.side_aliases.items()},
            python_extractor=rule.python_extractor,
            created_at=rule.created_at,
            distilled_from_label_ids=_str_list(rule.distilled_from_label_ids),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ParserRuleRow.rule_id],
            set_={
                "external_id": statement.excluded.external_id,
                "version": statement.excluded.version,
                "patterns": statement.excluded.patterns,
                "field_map": statement.excluded.field_map,
                "side_aliases": statement.excluded.side_aliases,
                "python_extractor": statement.excluded.python_extractor,
                "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
            },
        )
        session.execute(statement)


def read_parser_rules(
    session: Session, channel_id: int, user_id: UUID
) -> list[ParserRule]:
    rows = session.scalars(
        select(ParserRuleRow).where(
            ParserRuleRow.external_id == channel_id,
            ParserRuleRow.user_id == user_id,
        )
    ).all()
    return [
        ParserRule(
            rule_id=row.rule_id,
            user_id=row.user_id,
            channel_id=row.external_id,
            version=row.version,
            patterns=row.patterns,
            field_map=row.field_map,
            side_aliases=row.side_aliases,
            python_extractor=row.python_extractor,
            created_at=row.created_at,
            distilled_from_label_ids=row.distilled_from_label_ids,
        )
        for row in rows
    ]


def upsert_labels(session: Session, labels: list[GoldenLabel]) -> None:
    for label in labels:
        statement = pg_insert(GoldenLabelRow).values(
            id=label.id,
            user_id=label.user_id,
            external_id=label.channel_id,
            external_message_id=label.message_id,
            label=label.label.value,
            expected=(
                label.expected.model_dump(mode="json") if label.expected else None
            ),
            labeled_at=label.labeled_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["user_id", "external_id", "external_message_id"],
            set_={
                "label": statement.excluded.label,
                "expected": statement.excluded.expected,
                "labeled_at": statement.excluded.labeled_at,
            },
        )
        session.execute(statement)


def _label_from_row(row: GoldenLabelRow) -> GoldenLabel:
    return GoldenLabel(
        id=row.id,
        user_id=row.user_id,
        channel_id=row.external_id,
        message_id=row.external_message_id,
        label=row.label,
        expected=row.expected,
        labeled_at=row.labeled_at,
    )


def read_labels(session: Session, channel_id: int, user_id: UUID) -> list[GoldenLabel]:
    rows = session.scalars(
        select(GoldenLabelRow)
        .where(
            GoldenLabelRow.external_id == channel_id,
            GoldenLabelRow.user_id == user_id,
        )
        .order_by(GoldenLabelRow.labeled_at, GoldenLabelRow.external_message_id)
    ).all()
    return [_label_from_row(row) for row in rows]
