from datetime import UTC, datetime
from uuid import uuid4

import pytest

from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts.plans import PLAN_LIMITS, effective_plan


def _account(plan: Plan, status: str | None) -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="ada@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=plan,
        pending_email=None,
        cancel_at=None,
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
        subscription_status=status,
    )


def test_plan_limits_match_the_launch_pricing():
    assert PLAN_LIMITS[Plan.FREE].sources == 1
    assert PLAN_LIMITS[Plan.FREE].signals == 200
    assert PLAN_LIMITS[Plan.FREE].exchanges == 0
    assert PLAN_LIMITS[Plan.TRADER].sources == 10
    assert PLAN_LIMITS[Plan.TRADER].signals is None
    assert PLAN_LIMITS[Plan.TRADER].exchanges == 1
    assert PLAN_LIMITS[Plan.DESK].sources is None


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_paying_status_keeps_the_stored_plan(status):
    assert effective_plan(_account(Plan.TRADER, status)) is Plan.TRADER


@pytest.mark.parametrize(
    "status", [None, "past_due", "unpaid", "canceled", "incomplete", "paused"]
)
def test_non_paying_status_is_treated_as_free(status):
    assert effective_plan(_account(Plan.TRADER, status)) is Plan.FREE
