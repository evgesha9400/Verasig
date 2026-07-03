"""Mining Confirm: persist compiled rules, then re-derive everything (ADR 0015).

Confirm is the operator's ruleset becoming authoritative. It replaces the feed's
rules at a bumped version, re-derives candidates through the new filter,
re-extracts every event with the new parser, recomputes deletion-evidence
candidacy from the rules, and marks the feed verified — the real, server-side
status that supersedes the old frontend-only 'verified' patch.

Each step runs in its own transaction (via `session_factory`) so a long confirm
never holds one lock across the whole pipeline. Reuses the existing rules
`repository`, `candidate_derivation`, and `materialization` — Mining is just a
second rule producer alongside the legacy distillation loop.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.filter_rule import FilterRule
from verasig.domain.market_ports import Exchange
from verasig.domain.parser_rule import ParserRule
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.candidate_derivation import (
    derive_candidates,
    sweep_advisory,
)
from verasig.features.feeds.candidate_filter import apply_filter_rule
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.mining_schemas import MinedFilterRuleIn, MinedParserRuleIn
from verasig.features.signals import materialization
from verasig.features.signals.deterministic_parser import parse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MiningConfirmResult:
    version: int
    filter_rule_id: str
    parser_rule_ids: list[str]
    candidates_created: int
    parser_recovered: int
    signals_extracted: int
    unrecognized: int
    evidence_updated: int
    feed_status: str


def confirm_mining_rules(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    filter_rule_in: MinedFilterRuleIn,
    parser_rules_in: Sequence[MinedParserRuleIn],
    exchange: Exchange,
) -> MiningConfirmResult:
    version = _next_version(session_factory, user_id, external_id)
    filter_rule, parser_rules = _scope_rules(
        filter_rule_in, parser_rules_in, user_id, external_id, version
    )
    _replace_rules(session_factory, user_id, external_id, filter_rule, parser_rules)
    candidates_created = derive_candidates(
        session_factory, user_id, external_id, exchange, filter_rules=[filter_rule]
    )
    parser_recovered, _ = sweep_advisory(
        session_factory, user_id, external_id, parser_rules
    )
    extracted, unrecognized = _rematerialize(session_factory, user_id, external_id)
    evidence_updated = _recompute_evidence(
        session_factory, user_id, external_id, filter_rule, parser_rules
    )
    status = _mark_verified(session_factory, user_id, external_id)
    logger.info(
        "mining.confirm done: external_id=%s version=%s candidates=%s recovered=%s "
        "extracted=%s unrecognized=%s evidence_updated=%s status=%s",
        external_id,
        version,
        candidates_created,
        parser_recovered,
        extracted,
        unrecognized,
        evidence_updated,
        status,
    )
    return MiningConfirmResult(
        version=version,
        filter_rule_id=filter_rule.rule_id,
        parser_rule_ids=[rule.rule_id for rule in parser_rules],
        candidates_created=candidates_created,
        parser_recovered=parser_recovered,
        signals_extracted=extracted,
        unrecognized=unrecognized,
        evidence_updated=evidence_updated,
        feed_status=status,
    )


def _next_version(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> int:
    with session_factory() as session:
        return rule_repository.next_rule_version(session, user_id, external_id)


def _scope_rules(
    filter_rule_in: MinedFilterRuleIn,
    parser_rules_in: Sequence[MinedParserRuleIn],
    user_id: UUID,
    external_id: int,
    version: int,
) -> tuple[FilterRule, list[ParserRule]]:
    filter_rule = FilterRule(
        rule_id=f"{user_id}:{external_id}-mining-filter-v{version}",
        user_id=user_id,
        channel_id=external_id,
        version=version,
        include_patterns=filter_rule_in.include_patterns,
        exclude_patterns=filter_rule_in.exclude_patterns,
        display=filter_rule_in.display,
        distilled_from_label_ids=[],
    )
    parser_rules = [
        ParserRule(
            rule_id=f"{user_id}:{external_id}-mining-parser-{index + 1}-v{version}",
            user_id=user_id,
            channel_id=external_id,
            version=version,
            patterns=rule_in.patterns,
            field_map=rule_in.field_map,
            side_aliases=rule_in.side_aliases,
            distilled_from_label_ids=[],
        )
        for index, rule_in in enumerate(parser_rules_in)
    ]
    return filter_rule, parser_rules


def _replace_rules(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    filter_rule: FilterRule,
    parser_rules: list[ParserRule],
) -> None:
    with session_factory() as session:
        rule_repository.delete_feed_rules(session, user_id, external_id)
        rule_repository.upsert_filter_rule(session, filter_rule)
        rule_repository.upsert_parser_rules(session, parser_rules)
        session.commit()


def _rematerialize(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> tuple[int, int]:
    with session_factory() as session:
        counts = materialization.rematerialize_signal_outcomes(
            session, user_id, external_id
        )
        session.commit()
        return counts


def _text_is_signal(
    text: str | None, filter_rule: FilterRule, parser_rules: list[ParserRule]
) -> bool:
    if not text:
        return False
    if apply_filter_rule(filter_rule, text):
        return True
    return any(parse(rule, text) is not None for rule in parser_rules)


def _recompute_evidence(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    filter_rule: FilterRule,
    parser_rules: list[ParserRule],
) -> int:
    with session_factory() as session:
        candidate_ids = message_repository.candidate_message_ids(
            session, user_id, external_id
        )

    def decide(message_id: int, original_text: str | None) -> bool:
        return message_id in candidate_ids or _text_is_signal(
            original_text, filter_rule, parser_rules
        )

    with session_factory() as session:
        updated = deletion_repository.update_evidence_candidacy(
            session, user_id, external_id, decide
        )
        session.commit()
        return updated


def _mark_verified(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> str:
    with session_factory() as session:
        feed_repository.set_status(session, user_id, external_id, "verified")
        session.commit()
    return "verified"
