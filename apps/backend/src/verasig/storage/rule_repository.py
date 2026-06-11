"""Rule repository functions."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.parser_rule import ParserRule
from verasig.storage.models import FilterRuleRow, GoldenLabelRow, ParserRuleRow


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


def upsert_filter_rule(session: Session, rule: FilterRule) -> None:
    statement = pg_insert(FilterRuleRow).values(
        rule_id=rule.rule_id,
        channel_id=rule.channel_id,
        version=rule.version,
        include_patterns=rule.include_patterns,
        exclude_patterns=rule.exclude_patterns,
        matched_reason_template=rule.matched_reason_template,
        recall_target=rule.recall_target,
        python_filter=rule.python_filter,
        created_at=rule.created_at,
        distilled_from_label_ids=_str_list(rule.distilled_from_label_ids),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[FilterRuleRow.rule_id],
        set_={
            "channel_id": statement.excluded.channel_id,
            "version": statement.excluded.version,
            "include_patterns": statement.excluded.include_patterns,
            "exclude_patterns": statement.excluded.exclude_patterns,
            "matched_reason_template": statement.excluded.matched_reason_template,
            "recall_target": statement.excluded.recall_target,
            "python_filter": statement.excluded.python_filter,
            "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
        },
    )
    session.execute(statement)


def read_filter_rules(session: Session, channel_id: int) -> list[FilterRule]:
    rows = session.scalars(
        select(FilterRuleRow).where(FilterRuleRow.channel_id == channel_id)
    ).all()
    return [
        FilterRule(
            rule_id=row.rule_id,
            channel_id=row.channel_id,
            version=row.version,
            include_patterns=row.include_patterns,
            exclude_patterns=row.exclude_patterns,
            matched_reason_template=row.matched_reason_template,
            recall_target=row.recall_target,
            python_filter=row.python_filter,
            created_at=row.created_at,
            distilled_from_label_ids=row.distilled_from_label_ids,
        )
        for row in rows
    ]


def upsert_parser_rules(session: Session, rules: list[ParserRule]) -> None:
    for rule in rules:
        statement = pg_insert(ParserRuleRow).values(
            rule_id=rule.rule_id,
            channel_id=rule.channel_id,
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
                "channel_id": statement.excluded.channel_id,
                "version": statement.excluded.version,
                "patterns": statement.excluded.patterns,
                "field_map": statement.excluded.field_map,
                "side_aliases": statement.excluded.side_aliases,
                "python_extractor": statement.excluded.python_extractor,
                "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
            },
        )
        session.execute(statement)


def read_parser_rules(session: Session, channel_id: int) -> list[ParserRule]:
    rows = session.scalars(
        select(ParserRuleRow).where(ParserRuleRow.channel_id == channel_id)
    ).all()
    return [
        ParserRule(
            rule_id=row.rule_id,
            channel_id=row.channel_id,
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
            channel_id=label.channel_id,
            message_id=label.message_id,
            is_signal=label.is_signal,
            expected=(
                label.expected.model_dump(mode="json") if label.expected else None
            ),
            labeled_at=label.labeled_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["channel_id", "message_id"],
            set_={
                "is_signal": statement.excluded.is_signal,
                "expected": statement.excluded.expected,
                "labeled_at": statement.excluded.labeled_at,
            },
        )
        session.execute(statement)


def read_labels(session: Session, channel_id: int) -> list[GoldenLabel]:
    rows = session.scalars(
        select(GoldenLabelRow).where(GoldenLabelRow.channel_id == channel_id)
    ).all()
    return [
        GoldenLabel(
            id=row.id,
            channel_id=row.channel_id,
            message_id=row.message_id,
            is_signal=row.is_signal,
            expected=row.expected,
            labeled_at=row.labeled_at,
        )
        for row in rows
    ]
