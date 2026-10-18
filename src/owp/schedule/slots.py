"""Posting slot calculation.

Q3.9: America/New_York, nothing before 09:00 or after 22:00.
Q3.1 asked for research on cadence; see docs/requirements-decisions.md. The
default is 4 posts per week, which sits in the 3-5 range the sources converge
on, and `per_week` stays a parameter because the optimizer may vary posting
time (Q4.4) and because the evidence behind any specific number is thin.

Implemented rather than stubbed: pure date arithmetic, fully specified.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from owp.models import POSTING_TZ, QUIET_HOURS_END, QUIET_HOURS_START

DEFAULT_PER_WEEK = 4
#: Within the 09:00-22:00 window, these are the hours slots land on. Evening
#: first: engagement on short-form video skews later in the day.
PREFERRED_HOURS: tuple[int, ...] = (19, 12, 21, 17, 9)


def in_quiet_hours(moment: datetime) -> bool:
    """True when `moment` falls in the no-posting window (Q3.9)."""
    local = moment.astimezone(POSTING_TZ)
    return not (QUIET_HOURS_END <= local.hour < QUIET_HOURS_START)


def next_allowed(moment: datetime) -> datetime:
    """The earliest time at or after `moment` that is not in quiet hours."""
    local = moment.astimezone(POSTING_TZ)
    if local.hour < QUIET_HOURS_END:
        return local.replace(hour=QUIET_HOURS_END, minute=0, second=0, microsecond=0)
    if local.hour >= QUIET_HOURS_START:
        tomorrow = local + timedelta(days=1)
        return tomorrow.replace(hour=QUIET_HOURS_END, minute=0, second=0, microsecond=0)
    return local


def slots(after: datetime, count: int, *, per_week: int = DEFAULT_PER_WEEK) -> list[datetime]:
    """The next `count` posting slots strictly after `after`.

    Slots are spread evenly across the week at the preferred hours, so a
    4-per-week cadence lands roughly every other day rather than four days
    running.

    Args:
        after: Slots returned are strictly later than this.
        count: How many slots to return.
        per_week: Posts per week; must be at least 1.

    Returns:
        `count` timezone-aware datetimes in America/New_York, ascending, none
        in quiet hours.
    """
    if per_week < 1:
        raise ValueError("per_week must be >= 1")
    if count < 0:
        raise ValueError("count must be >= 0")

    spacing = timedelta(days=7 / per_week)
    cursor = next_allowed(after)
    out: list[datetime] = []

    while len(out) < count:
        hour = PREFERRED_HOURS[len(out) % len(PREFERRED_HOURS)]
        candidate = cursor.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= after or in_quiet_hours(candidate):
            candidate = next_allowed(max(candidate, cursor) + timedelta(hours=1))
        if out and candidate <= out[-1]:
            candidate = next_allowed(out[-1] + spacing)
        out.append(candidate)
        cursor = next_allowed(candidate + spacing)

    return out
