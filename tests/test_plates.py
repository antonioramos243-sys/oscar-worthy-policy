from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owp.budget import WEEKLY_CAP_USD, Charge
from owp.models import VisualStyle
from owp.render.plates import (
    PLATE_SECONDS,
    NoPlatesForStyle,
    Plate,
    PlateLibrary,
)

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
RATE = 0.05


def plate(pid: str, style: VisualStyle, *, generated: bool = True) -> Plate:
    return Plate(
        id=pid,
        style=style,
        prompt="placeholder",
        path=f"{pid}.mp4" if generated else None,
    )


def library(*plates: Plate) -> PlateLibrary:
    return PlateLibrary(list(plates))


def test_shipped_manifest_loads() -> None:
    assert PlateLibrary.load().plates


def test_pending_and_generated_split() -> None:
    lib = library(
        plate("a", VisualStyle.FLAT),
        plate("b", VisualStyle.FLAT, generated=False),
    )
    assert [p.id for p in lib.generated()] == ["a"]
    assert [p.id for p in lib.pending()] == ["b"]


def test_cover_returns_enough_plates_for_the_duration() -> None:
    lib = library(plate("a", VisualStyle.FLAT), plate("b", VisualStyle.FLAT))
    chosen = lib.cover(VisualStyle.FLAT, 20.0)
    assert sum(p.seconds for p in chosen) >= 20.0
    assert len(chosen) == 3  # 8s plates


def test_cover_cycles_plates_when_more_time_is_needed() -> None:
    lib = library(plate("a", VisualStyle.FLAT), plate("b", VisualStyle.FLAT))
    assert [p.id for p in lib.cover(VisualStyle.FLAT, 30.0)] == ["a", "b", "a", "b"]


def test_cover_is_deterministic() -> None:
    lib = library(plate("a", VisualStyle.FLAT), plate("b", VisualStyle.FLAT))
    assert lib.cover(VisualStyle.FLAT, 24.0) == lib.cover(VisualStyle.FLAT, 24.0)


def test_cover_ignores_other_styles() -> None:
    lib = library(plate("a", VisualStyle.FLAT), plate("n", VisualStyle.NOIR))
    assert [p.id for p in lib.cover(VisualStyle.NOIR, 8.0)] == ["n"]


def test_cover_ignores_ungenerated_plates() -> None:
    lib = library(plate("a", VisualStyle.FLAT, generated=False))
    with pytest.raises(NoPlatesForStyle, match="1 plates are pending"):
        lib.cover(VisualStyle.FLAT, 8.0)


def test_cover_rejects_negative_duration() -> None:
    lib = library(plate("a", VisualStyle.FLAT))
    with pytest.raises(ValueError):
        lib.cover(VisualStyle.FLAT, -1.0)


def test_zero_duration_needs_no_plates() -> None:
    lib = library(plate("a", VisualStyle.FLAT))
    assert lib.cover(VisualStyle.FLAT, 0.0) == []


def test_generation_cost_is_per_second() -> None:
    lib = library(plate("a", VisualStyle.FLAT), plate("b", VisualStyle.FLAT))
    assert lib.generation_cost(lib.plates, usd_per_second=RATE) == pytest.approx(
        2 * PLATE_SECONDS * RATE
    )


def test_affordable_batch_truncates_to_the_weekly_cap() -> None:
    # 100 pending plates would cost $40; only $25 of cap exists.
    lib = library(*(plate(f"p{i}", VisualStyle.FLAT, generated=False) for i in range(100)))
    batch = lib.affordable_batch([], NOW, usd_per_second=RATE)
    assert lib.generation_cost(batch, usd_per_second=RATE) <= WEEKLY_CAP_USD
    assert len(batch) == 62  # 62 * 8s * $0.05 = $24.80


def test_affordable_batch_reserving_the_weeks_video_cost() -> None:
    # Reserve the $0.64 that four videos cost, spend the rest on the library.
    lib = library(*(plate(f"p{i}", VisualStyle.FLAT, generated=False) for i in range(100)))
    batch = lib.affordable_batch([], NOW, usd_per_second=RATE, reserve_usd=0.64)
    cost = lib.generation_cost(batch, usd_per_second=RATE)
    assert cost <= WEEKLY_CAP_USD - 0.64
    assert len(batch) == 60  # 60 * $0.40 = $24.00; a 61st would breach $24.36


def test_affordable_batch_shrinks_as_the_reserve_grows() -> None:
    lib = library(*(plate(f"p{i}", VisualStyle.FLAT, generated=False) for i in range(100)))
    big_reserve = lib.affordable_batch([], NOW, usd_per_second=RATE, reserve_usd=24.36)
    small_reserve = lib.affordable_batch([], NOW, usd_per_second=RATE, reserve_usd=0.64)
    assert len(big_reserve) == 1  # $0.64 left, $0.40 a plate
    assert len(big_reserve) < len(small_reserve)


def test_affordable_batch_accounts_for_spend_already_booked() -> None:
    lib = library(*(plate(f"p{i}", VisualStyle.FLAT, generated=False) for i in range(100)))
    spent = [Charge(at=NOW, usd=24.0)]
    batch = lib.affordable_batch(spent, NOW, usd_per_second=RATE)
    assert len(batch) == 2  # $1 left, $0.40 a plate


def test_affordable_batch_is_empty_when_the_week_is_exhausted() -> None:
    lib = library(*(plate(f"p{i}", VisualStyle.FLAT, generated=False) for i in range(10)))
    assert lib.affordable_batch([Charge(at=NOW, usd=25.0)], NOW, usd_per_second=RATE) == []


def test_affordable_batch_is_empty_when_nothing_is_pending() -> None:
    assert library(plate("a", VisualStyle.FLAT)).affordable_batch([], NOW) == []
