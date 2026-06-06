"""Streamlit distillation workbench.

The pure model in `ui.workbench` decides candidate buckets and metrics. This
adapter owns operator state: labeling messages, persisting labels, distilling
rules, and rendering each Telegram message as a distinct review unit.
"""

import os
import re
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import streamlit as st

from verasig.config import Settings
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.foundation.db import make_session_factory
from verasig.foundation.static_exchange import StaticExchange
from verasig.services.distillation.rule_distiller import ClaudeCliDistiller
from verasig.services.distillation.workbench import distil_step
from verasig.storage import repositories as repo
from verasig.ui.workbench import view_model

_CANDIDATES = "Candidates"
_UNFLAGGED = "Unflagged"
_DRIFT = "Drift"
_AUDIT = "Audit"
_ALL = "All"
_VIEW_NAMES = (_CANDIDATES, _UNFLAGGED, _DRIFT, _AUDIT, _ALL)
_EMPTY = ""
_TAKE_PROFIT_SEPARATOR = re.compile(r"[,\\s]+")


def _bootstrap_from_db() -> dict:
    settings = Settings()
    session_factory = make_session_factory(settings.database_url)
    channel_id = int(os.environ["VERASIG_WORKBENCH_CHANNEL"])
    with session_factory() as session:
        channel = repo.find_channel(session, channel_id)
        messages = repo.read_messages(session, channel_id)
        labels = repo.read_labels(session, channel_id)
        filter_rules = repo.read_filter_rules(session, channel_id)
        parser_rules = repo.read_parser_rules(session, channel_id)
        drift_ids = {
            warning.message_id
            for warning in repo.read_drift_warnings(session, channel_id)
        }
    return {
        "channel_id": channel_id,
        "title": channel.title if channel else str(channel_id),
        "messages": messages,
        "labels": labels,
        "filter_rule": _latest(filter_rules),
        "parser_rules": parser_rules,
        "drift_ids": drift_ids,
        "exchange": StaticExchange(),
        "distiller": ClaudeCliDistiller(command=settings.distiller_command),
        "session_factory": session_factory,
    }


def _latest(items: list):
    if not items:
        return None
    return max(items, key=lambda item: (item.version, item.created_at))


def _bootstrap() -> dict:
    return st.session_state.get("bootstrap") or _bootstrap_from_db()


def _labels_by_message(labels: list[GoldenLabel]) -> dict[int, GoldenLabel]:
    return {label.message_id: label for label in labels}


def _init_state(boot: dict) -> None:
    st.session_state.setdefault("labels_by_message", _labels_by_message(boot["labels"]))
    st.session_state.setdefault("filter_rule", boot.get("filter_rule"))
    st.session_state.setdefault("parser_rules", boot.get("parser_rules", []))


def _current_labels() -> list[GoldenLabel]:
    labels = list(st.session_state["labels_by_message"].values())
    return sorted(labels, key=lambda label: label.message_id)


def _save_label(boot: dict, label: GoldenLabel) -> None:
    st.session_state["labels_by_message"][label.message_id] = label
    session_factory = boot.get("session_factory")
    if session_factory is None:
        return
    with session_factory() as session:
        repo.upsert_labels(session, [label])
        session.commit()


def _save_rules(boot: dict, filter_rule, parser_rules: list) -> None:
    st.session_state["filter_rule"] = filter_rule
    st.session_state["parser_rules"] = parser_rules
    session_factory = boot.get("session_factory")
    if session_factory is None:
        return
    with session_factory() as session:
        repo.upsert_filter_rule(session, filter_rule)
        repo.upsert_parser_rules(session, parser_rules)
        session.commit()


def _build_noise_label(message: RawTelegramMessage) -> GoldenLabel:
    return GoldenLabel(
        channel_id=message.channel_id,
        message_id=message.message_id,
        is_signal=False,
    )


def _build_signal_label(
    message: RawTelegramMessage, expected: ExtractedSignal | None = None
) -> GoldenLabel:
    return GoldenLabel(
        channel_id=message.channel_id,
        message_id=message.message_id,
        is_signal=True,
        expected=expected,
    )


def _parse_decimal(raw: str) -> Decimal | None:
    text = raw.strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"{raw!r} is not a valid number") from error


def _parse_take_profits(raw: str) -> list[Decimal]:
    values = []
    for item in _TAKE_PROFIT_SEPARATOR.split(raw.strip()):
        if item:
            values.append(_parse_decimal(item))
    return [value for value in values if value is not None]


def _expected_from_fields(
    message: RawTelegramMessage,
    *,
    symbol: str,
    side: str,
    entry_type: str,
    entry_low: str,
    entry_high: str,
    stop_loss: str,
    take_profits: str,
    leverage: str,
    confidence: str,
) -> ExtractedSignal:
    if not symbol.strip():
        raise ValueError("symbol is required for expected fields")
    if not side:
        raise ValueError("side is required for expected fields")
    selected_entry_type = EntryType(entry_type) if entry_type else None
    return ExtractedSignal(
        event_id=uuid4(),
        channel_id=message.channel_id,
        symbol=symbol,
        side=Side(side),
        entry_type=selected_entry_type,
        entry_low=_parse_decimal(entry_low),
        entry_high=_parse_decimal(entry_high),
        stop_loss=_parse_decimal(stop_loss),
        take_profits=_parse_take_profits(take_profits),
        leverage=_parse_decimal(leverage),
        confidence=_parse_decimal(confidence),
    )


def _render_metrics(model: dict, labels: list[GoldenLabel]) -> None:
    positives = sum(1 for label in labels if label.is_signal)
    negatives = len(labels) - positives
    cols = st.columns(6)
    cols[0].metric("labels", len(labels))
    cols[1].metric("signals", positives)
    cols[2].metric("noise", negatives)
    cols[3].metric("candidates", len(model["candidate_ids"]))
    cols[4].metric("residue", len(model["residue"]))
    cols[5].metric("filter recall", round(model["recall"], 2))


def _render_distill_controls(boot: dict, labels: list[GoldenLabel]) -> None:
    disabled = not labels
    if st.button("Distil rules from labels", disabled=disabled, type="primary"):
        filter_rule, parser_rules = distil_step(labels, boot["distiller"])
        _save_rules(boot, filter_rule, parser_rules)
        st.success(
            f"saved {filter_rule.rule_id} and {len(parser_rules)} parser rule(s)"
        )
    parser_rules = st.session_state["parser_rules"]
    filter_rule = st.session_state["filter_rule"]
    rule_name = filter_rule.rule_id if filter_rule else "none"
    st.caption(f"filter rule: {rule_name} · parser rules: {len(parser_rules)}")


def _messages_for_view(view: str, boot: dict, model: dict) -> list[RawTelegramMessage]:
    panels = {
        _CANDIDATES: model["views"].candidates,
        _UNFLAGGED: model["views"].unflagged,
        _DRIFT: model["views"].drift,
        _AUDIT: model["views"].audit,
        _ALL: boot["messages"],
    }
    return panels[view]


def _filter_visible_messages(
    messages: list[RawTelegramMessage],
    *,
    query: str,
    only_unlabeled: bool,
    labels_by_message: dict[int, GoldenLabel],
) -> list[RawTelegramMessage]:
    visible = messages
    if only_unlabeled:
        visible = [
            message
            for message in visible
            if message.message_id not in labels_by_message
        ]
    if query.strip():
        needle = query.casefold().strip()
        visible = [
            message
            for message in visible
            if needle in (message.text or "").casefold()
            or needle in str(message.message_id)
        ]
    return visible


def _label_badge(label: GoldenLabel | None) -> str:
    if label is None:
        return "unlabeled"
    return "signal" if label.is_signal else "noise"


def _message_badges(
    message: RawTelegramMessage,
    *,
    label: GoldenLabel | None,
    candidate_ids: set[int],
    drift_ids: set[int],
) -> str:
    badges = [_label_badge(label)]
    if message.message_id in candidate_ids:
        badges.append("candidate")
    if message.message_id in drift_ids:
        badges.append("drift")
    return " · ".join(badges)


def _format_when(message: RawTelegramMessage) -> str:
    return message.posted_at.strftime("%Y-%m-%d %H:%M")


def _expected_defaults(label: GoldenLabel | None) -> dict[str, str]:
    expected = label.expected if label and label.expected else None
    if expected is None:
        return {
            "symbol": "",
            "side": "",
            "entry_type": "",
            "entry_low": "",
            "entry_high": "",
            "stop_loss": "",
            "take_profits": "",
            "leverage": "",
            "confidence": "",
        }
    return {
        "symbol": expected.symbol,
        "side": expected.side.value,
        "entry_type": expected.entry_type.value if expected.entry_type else "",
        "entry_low": str(expected.entry_low or ""),
        "entry_high": str(expected.entry_high or ""),
        "stop_loss": str(expected.stop_loss or ""),
        "take_profits": ", ".join(str(value) for value in expected.take_profits),
        "leverage": str(expected.leverage or ""),
        "confidence": str(expected.confidence or ""),
    }


def _render_expected_form(
    boot: dict, message: RawTelegramMessage, label: GoldenLabel | None
) -> None:
    defaults = _expected_defaults(label)
    with st.expander("Expected fields", expanded=bool(label and label.expected)):
        with st.form(f"expected_{message.message_id}", border=False):
            first = st.columns(3)
            symbol = first[0].text_input(
                "symbol",
                value=defaults["symbol"],
                key=f"symbol_{message.message_id}",
            )
            side = first[1].selectbox(
                "side",
                ["", Side.LONG.value, Side.SHORT.value],
                index=["", Side.LONG.value, Side.SHORT.value].index(defaults["side"]),
                key=f"side_{message.message_id}",
            )
            entry_type = first[2].selectbox(
                "entry type",
                ["", *(item.value for item in EntryType)],
                index=["", *(item.value for item in EntryType)].index(
                    defaults["entry_type"]
                ),
                key=f"entry_type_{message.message_id}",
            )
            second = st.columns(3)
            entry_low = second[0].text_input(
                "entry low",
                value=defaults["entry_low"],
                key=f"entry_low_{message.message_id}",
            )
            entry_high = second[1].text_input(
                "entry high",
                value=defaults["entry_high"],
                key=f"entry_high_{message.message_id}",
            )
            stop_loss = second[2].text_input(
                "stop loss",
                value=defaults["stop_loss"],
                key=f"stop_loss_{message.message_id}",
            )
            third = st.columns(3)
            take_profits = third[0].text_input(
                "take profits",
                value=defaults["take_profits"],
                key=f"take_profits_{message.message_id}",
            )
            leverage = third[1].text_input(
                "leverage",
                value=defaults["leverage"],
                key=f"leverage_{message.message_id}",
            )
            confidence = third[2].text_input(
                "confidence",
                value=defaults["confidence"],
                key=f"confidence_{message.message_id}",
            )
            if st.form_submit_button("Save signal + fields"):
                try:
                    expected = _expected_from_fields(
                        message,
                        symbol=symbol,
                        side=side,
                        entry_type=entry_type,
                        entry_low=entry_low,
                        entry_high=entry_high,
                        stop_loss=stop_loss,
                        take_profits=take_profits,
                        leverage=leverage,
                        confidence=confidence,
                    )
                except ValueError as error:
                    st.error(str(error))
                    return
                _save_label(boot, _build_signal_label(message, expected))
                st.rerun()


def _render_message_card(
    boot: dict,
    message: RawTelegramMessage,
    *,
    label: GoldenLabel | None,
    candidate_ids: set[int],
    drift_ids: set[int],
) -> None:
    with st.container(border=True):
        header = st.columns([1, 2, 3])
        header[0].markdown(f"**#{message.message_id}**")
        header[1].caption(_format_when(message))
        header[2].caption(
            _message_badges(
                message,
                label=label,
                candidate_ids=candidate_ids,
                drift_ids=drift_ids,
            )
        )
        st.code(message.text or "[empty message]", language=None)
        actions = st.columns([1, 1, 4])
        if actions[0].button("Signal", key=f"signal_{message.message_id}"):
            _save_label(boot, _build_signal_label(message))
            st.rerun()
        if actions[1].button("Noise", key=f"noise_{message.message_id}"):
            _save_label(boot, _build_noise_label(message))
            st.rerun()
        _render_expected_form(boot, message, label)


def _render_messages(boot: dict, model: dict) -> None:
    labels_by_message = st.session_state["labels_by_message"]
    controls = st.columns([2, 2, 1])
    view = controls[0].radio("View", _VIEW_NAMES, horizontal=True)
    query = controls[1].text_input("Search", value="")
    only_unlabeled = controls[2].checkbox("Unlabeled", value=False)
    messages = _messages_for_view(view, boot, model)
    visible = _filter_visible_messages(
        messages,
        query=query,
        only_unlabeled=only_unlabeled,
        labels_by_message=labels_by_message,
    )
    st.caption(f"showing {len(visible)} of {len(messages)} messages")
    for message in visible:
        _render_message_card(
            boot,
            message,
            label=labels_by_message.get(message.message_id),
            candidate_ids=model["candidate_ids"],
            drift_ids=boot["drift_ids"],
        )


def main() -> None:
    st.set_page_config(page_title="Verasig Workbench", layout="wide")
    boot = _bootstrap()
    _init_state(boot)
    labels = _current_labels()
    st.title(f"Distillation workbench - {boot['title']}")
    _render_distill_controls(boot, labels)
    model = view_model(
        boot["messages"],
        labels,
        st.session_state["filter_rule"],
        st.session_state["parser_rules"],
        drift_ids=boot["drift_ids"],
        exchange=boot["exchange"],
    )
    _render_metrics(model, labels)
    _render_messages(boot, model)


main()
