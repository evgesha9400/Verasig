"""Streamlit workbench smoke test (test-plan §1 smoke layer; optional).

Drives label → distil → filter → iterate through `streamlit.testing` with a fake
distiller injected via session_state (no DB, no real LLM). Asserts the loop wires
up: distilling broadens the candidate set and the recall meter lights up.
"""

from datetime import datetime, timezone
from pathlib import Path

from fakes import FakeDistiller, FakeExchange
from streamlit.testing.v1 import AppTest

from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage

_APP = str(Path(__file__).parent.parent.parent / "src" / "verasig" / "ui" / "app.py")
_DISTILL = (
    Path(__file__).parent.parent / "fixtures" / "cli" / "distill_pilot.txt"
).read_text(encoding="utf-8")


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _msg(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={},
    )


def _bootstrap() -> dict:
    # seed flags only the BTC signal; the distilled broad filter flags all three
    return {
        "title": "Pilot",
        "messages": [
            _msg(1, "BTC long entry 65000"),
            _msg(2, "gm frens wagmi"),
            _msg(3, "hello world friends"),
        ],
        "labels": [GoldenLabel(channel_id=7, message_id=1, is_signal=True)],
        "drift_ids": set(),
        "exchange": FakeExchange({"BTC"}),
        "distiller": FakeDistiller(_DISTILL),
    }


def _metric(app_test, label: str) -> float:
    for metric in app_test.metric:
        if metric.label == label:
            return float(metric.value)
    raise AssertionError(f"no metric labeled {label!r}")


def test_workbench_loop_label_distil_filter_iterate():
    app_test = AppTest.from_file(_APP)
    app_test.session_state["bootstrap"] = _bootstrap()
    app_test.run()
    assert not app_test.exception
    candidates_before = _metric(app_test, "candidates")
    assert candidates_before == 1  # seed-only flags just the BTC signal

    app_test.button[0].click()
    app_test.run()
    assert not app_test.exception
    assert _metric(app_test, "candidates") > candidates_before  # distil broadened
    assert _metric(app_test, "filter recall") == 1.0  # the signal is now flagged


def test_workbench_view_switcher_renders_each_panel():
    app_test = AppTest.from_file(_APP)
    app_test.session_state["bootstrap"] = _bootstrap()
    app_test.run()
    for view in ("Candidates", "Unflagged", "⚠ Drift", "🎲 Audit"):
        app_test.radio[0].set_value(view)
        app_test.run()
        assert not app_test.exception
