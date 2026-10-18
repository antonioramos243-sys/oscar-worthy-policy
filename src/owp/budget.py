"""Weekly spend ledger.

Q2.10 caps weekly operational cost at $25. That is a hard cap on a pipeline
whose dominant cost is billed per second of generated video, so it is enforced
in code rather than left to a billing alert that arrives after the money is
gone.

Implemented rather than stubbed: it is arithmetic over a spend log, it depends
on no undecided requirement, and it is the one guard that is useless if added
late.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

WEEKLY_CAP_USD = 25.0


class BudgetExceeded(RuntimeError):
    """Raised when a charge would take the week past its cap."""


@dataclass(frozen=True)
class Charge:
    """One billed operation."""

    at: datetime
    usd: float
    kind: str = "video"
    note: str | None = None


def iso_week(moment: datetime | date) -> tuple[int, int]:
    """The ISO (year, week) a moment falls in, used to bucket spend."""
    cal = moment.isocalendar()
    return cal[0], cal[1]


def spent_in_week(charges: Iterable[Charge], moment: datetime) -> float:
    """Total already charged in `moment`'s ISO week."""
    week = iso_week(moment)
    return sum(c.usd for c in charges if iso_week(c.at) == week)


def remaining(charges: Iterable[Charge], moment: datetime, cap: float = WEEKLY_CAP_USD) -> float:
    """Budget left in `moment`'s week. Never negative."""
    return max(0.0, cap - spent_in_week(charges, moment))


def check_affordable(
    charges: Iterable[Charge],
    moment: datetime,
    cost_usd: float,
    *,
    cap: float = WEEKLY_CAP_USD,
) -> None:
    """Raise if `cost_usd` would breach the weekly cap.

    Called before generating, not after: the point is to not spend the money.

    Raises:
        BudgetExceeded: if the charge does not fit in the remaining budget.
    """
    left = remaining(charges, moment, cap)
    if cost_usd > left:
        year, week = iso_week(moment)
        raise BudgetExceeded(
            f"${cost_usd:.2f} would exceed the ${cap:.2f} cap for {year}-W{week:02d}; "
            f"${left:.2f} remains"
        )


def estimate_generative_cost(seconds: float, usd_per_second: float) -> float:
    """Cost of generating `seconds` of video at a per-second rate.

    Per-second billing is what makes the cap tight: see
    docs/requirements-decisions.md for the tier comparison against $25/week.
    """
    if seconds < 0 or usd_per_second < 0:
        raise ValueError("seconds and rate must be non-negative")
    return seconds * usd_per_second
