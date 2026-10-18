"""The variant space the optimizer is allowed to explore.

Q4.4 permits any of format, hook, length, voice, visual style, posting time,
caption style, company and category - but caps the count at about five,
because more than that cannot be optimized at realistic volume. These are the
five, chosen for the largest expected effect per unit of traffic:

  1. format        - the biggest swing in how a video lands
  2. hook_style    - decides the first two seconds, which decide retention
  3. length_bucket - 30-90s is a wide range (Q2.3)
  4. visual_style  - within the animation direction set by Q2.4
  5. posting_hour  - cheap to vary, and the one variable that costs nothing

Deliberately NOT variables:
  - tone and accuracy: Q4.6 makes them hard constraints the optimizer may
    never trade off, so they are not in the space at all. A constraint that is
    merely weighted is a constraint that eventually gets traded.
  - voice: Q2.5 settles synthetic voice, and per-character voices belong to the
    cast (Q2.4), not to a bandit.
  - company/category: the 40 targets are the point of the project, not a lever.
    Letting a bandit drop unpopular companies would quietly defeat Q4.2.
"""

from __future__ import annotations

import itertools
from enum import StrEnum

from pydantic import BaseModel

from owp.models import NarrativeFormat, VisualStyle


class HookStyle(StrEnum):
    QUESTION = "question"
    CLAIM = "claim"
    QUOTE = "quote"


class LengthBucket(StrEnum):
    """Buckets across the 30-90s range (Q2.3)."""

    SHORT = "30s"
    MEDIUM = "60s"
    LONG = "90s"

    @property
    def seconds(self) -> float:
        return {"30s": 30.0, "60s": 60.0, "90s": 90.0}[self.value]


#: Hours the optimizer may choose, all inside the 09:00-22:00 window (Q3.9).
POSTING_HOURS: tuple[int, ...] = (9, 12, 17, 19, 21)


class Arm(BaseModel, frozen=True):
    """One point in the variant space."""

    format: NarrativeFormat
    hook_style: HookStyle
    length_bucket: LengthBucket
    visual_style: VisualStyle
    posting_hour: int

    def key(self) -> str:
        return (
            f"{self.format.value}|{self.hook_style.value}|{self.length_bucket.value}"
            f"|{self.visual_style.value}|{self.posting_hour}"
        )


def all_arms() -> list[Arm]:
    """Every combination in the space.

    Note the size: 5 formats x 3 hooks x 3 lengths x 3 styles x 5 hours = 675
    arms. At four posts a week that is far more arms than observations, which is
    exactly why Q4.4 caps the variable count - and why the bandit must share
    evidence across arms per variable rather than treat each as independent.
    See `owp.optimize.bandit`.
    """
    return [
        Arm(
            format=f,
            hook_style=h,
            length_bucket=length,
            visual_style=v,
            posting_hour=hour,
        )
        for f, h, length, v, hour in itertools.product(
            NarrativeFormat, HookStyle, LengthBucket, VisualStyle, POSTING_HOURS
        )
    ]
