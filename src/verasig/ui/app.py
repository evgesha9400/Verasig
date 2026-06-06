"""Streamlit distillation workbench — thin adapter over the pure view-model.

The 4-view loop (Candidates | Unflagged | ⚠ Drift | 🎲 Audit), the recall/precision
meters, and the Distil button all delegate to `ui.workbench.view_model` +
`services.distillation` (unit-tested). Tests inject a `bootstrap` into
`st.session_state` (offline, FakeDistiller); production loads it from the DB for
the channel the `workbench` CLI launched.
"""

import os

import streamlit as st

from verasig.config import Settings
from verasig.foundation.db import make_session_factory
from verasig.foundation.exchange import StaticExchange
from verasig.services.distillation.rule_distiller import ClaudeCliDistiller
from verasig.services.distillation.workbench import distil_step
from verasig.storage import repositories as repo
from verasig.ui.workbench import view_model

_CANDIDATES, _UNFLAGGED, _DRIFT, _AUDIT = (
    "Candidates",
    "Unflagged",
    "⚠ Drift",
    "🎲 Audit",
)


def _bootstrap_from_db() -> dict:
    settings = Settings()
    session_factory = make_session_factory(settings.database_url)
    channel_id = int(os.environ["VERASIG_WORKBENCH_CHANNEL"])
    with session_factory() as session:
        channel = repo.find_channel(session, channel_id)
        messages = repo.read_messages(session, channel_id)
        labels = repo.read_labels(session, channel_id)
        drift_ids = {
            warning.message_id
            for warning in repo.read_drift_warnings(session, channel_id)
        }
    return {
        "title": channel.title if channel else str(channel_id),
        "messages": messages,
        "labels": labels,
        "drift_ids": drift_ids,
        "exchange": StaticExchange(),
        "distiller": ClaudeCliDistiller(command=settings.distiller_command),
    }


def _bootstrap() -> dict:
    return st.session_state.get("bootstrap") or _bootstrap_from_db()


def main() -> None:
    boot = _bootstrap()
    st.session_state.setdefault("filter_rule", None)
    st.session_state.setdefault("parser_rules", [])
    st.title(f"Distillation workbench — {boot['title']}")

    # button first so a click is reflected in the model rendered this run
    if st.button("Distil rules from labels"):
        filter_rule, parser_rules = distil_step(boot["labels"], boot["distiller"])
        st.session_state["filter_rule"] = filter_rule
        st.session_state["parser_rules"] = parser_rules

    model = view_model(
        boot["messages"],
        boot["labels"],
        st.session_state["filter_rule"],
        st.session_state["parser_rules"],
        drift_ids=boot["drift_ids"],
        exchange=boot["exchange"],
    )
    st.metric("filter recall", round(model["recall"], 2))
    st.metric("parser precision", round(model["parser_precision"], 2))
    st.metric("residue", len(model["residue"]))
    st.metric("candidates", len(model["candidate_ids"]))

    panels = {
        _CANDIDATES: model["views"].candidates,
        _UNFLAGGED: model["views"].unflagged,
        _DRIFT: model["views"].drift,
        _AUDIT: model["views"].audit,
    }
    view = st.radio("View", list(panels))
    for message in panels[view]:
        st.write(f"#{message.message_id} {message.text}")


main()
