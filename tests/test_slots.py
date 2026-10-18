from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from owp.models import POSTING_TZ
from owp.schedule.slots import in_quiet_hours, next_allowed, slots


def et(y: int, m: int, d: int, h: int) -> datetime:
    return datetime(y, m, d, h, 0, tzinfo=POSTING_TZ)


def test_quiet_hours_boundaries() -> None:
    assert in_quiet_hours(et(2026, 10, 19, 8))
    assert not in_quiet_hours(et(2026, 10, 19, 9))
    assert not in_quiet_hours(et(2026, 10, 19, 21))
    assert in_quiet_hours(et(2026, 10, 19, 22))


def test_next_allowed_moves_early_morning_to_nine() -> None:
    assert next_allowed(et(2026, 10, 19, 3)).hour == 9


def test_next_allowed_moves_late_night_to_next_morning() -> None:
    moved = next_allowed(et(2026, 10, 19, 23))
    assert moved.hour == 9
    assert moved.day == 20


def test_no_slot_lands_in_quiet_hours() -> None:
    assert not any(in_quiet_hours(s) for s in slots(et(2026, 10, 19, 23), 20))


def test_slots_are_strictly_increasing_and_after_the_start() -> None:
    start = et(2026, 10, 19, 10)
    got = slots(start, 12)
    assert all(s > start for s in got)
    assert got == sorted(got)
    assert len(set(got)) == len(got)


def test_four_per_week_spreads_across_the_week() -> None:
    got = slots(et(2026, 10, 19, 0), 4, per_week=4)
    span = got[-1] - got[0]
    assert timedelta(days=4) <= span <= timedelta(days=7)


def test_higher_cadence_packs_slots_closer() -> None:
    sparse = slots(et(2026, 10, 19, 0), 4, per_week=2)
    dense = slots(et(2026, 10, 19, 0), 4, per_week=7)
    assert dense[-1] - dense[0] < sparse[-1] - sparse[0]


def test_zero_count_returns_nothing() -> None:
    assert slots(et(2026, 10, 19, 10), 0) == []


def test_invalid_cadence_rejected() -> None:
    with pytest.raises(ValueError):
        slots(et(2026, 10, 19, 10), 1, per_week=0)
