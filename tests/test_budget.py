from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owp.budget import (
    WEEKLY_CAP_USD,
    BudgetExceeded,
    Charge,
    check_affordable,
    estimate_generative_cost,
    remaining,
    spent_in_week,
)

MON = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)   # ISO week 43
SUN = datetime(2026, 10, 25, 23, 0, tzinfo=UTC)   # same ISO week
NEXT_MON = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)  # week 44


def test_cap_is_twenty_five() -> None:
    assert WEEKLY_CAP_USD == 25.0


def test_spend_buckets_by_iso_week() -> None:
    charges = [Charge(at=MON, usd=10.0), Charge(at=SUN, usd=5.0), Charge(at=NEXT_MON, usd=7.0)]
    assert spent_in_week(charges, MON) == 15.0
    assert spent_in_week(charges, NEXT_MON) == 7.0


def test_budget_resets_the_following_week() -> None:
    charges = [Charge(at=MON, usd=25.0)]
    assert remaining(charges, MON) == 0.0
    assert remaining(charges, NEXT_MON) == 25.0


def test_affordable_charge_passes() -> None:
    check_affordable([Charge(at=MON, usd=20.0)], MON, 5.0)


def test_charge_over_cap_raises() -> None:
    with pytest.raises(BudgetExceeded, match="2026-W43"):
        check_affordable([Charge(at=MON, usd=20.0)], MON, 5.01)


def test_remaining_never_negative() -> None:
    assert remaining([Charge(at=MON, usd=99.0)], MON) == 0.0


def test_generative_cost_is_per_second() -> None:
    # Veo 3.1 Lite 720p, 60s.
    assert estimate_generative_cost(60, 0.05) == pytest.approx(3.0)


def test_four_sixty_second_videos_fit_only_at_the_lite_tier() -> None:
    # The decision recorded in docs/requirements-decisions.md.
    weekly = lambda rate: 4 * estimate_generative_cost(60, rate)  # noqa: E731
    assert weekly(0.05) <= WEEKLY_CAP_USD    # Lite 720p
    assert weekly(0.08) <= WEEKLY_CAP_USD    # Lite 1080p
    assert weekly(0.20) > WEEKLY_CAP_USD     # Fast
    assert weekly(0.50) > WEEKLY_CAP_USD     # Standard


def test_negative_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        estimate_generative_cost(-1, 0.05)
