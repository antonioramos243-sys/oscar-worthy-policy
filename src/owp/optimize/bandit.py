"""A factored epsilon-greedy bandit over the five variables.

Q4.5 asks for an automated optimizer rather than a dashboard. The volume makes
the obvious implementation wrong: the space has 675 arms (see
`owp.optimize.arms.all_arms`) and the cadence is about four posts a week, so a
per-arm bandit would still be on its first pull of most arms years from now.

So this learns per *variable* instead. Each of the five dimensions keeps its own
value estimate per level, every observation updates all five, and selection
picks each dimension independently. That trades the ability to find interactions
- "noir only works for horror-story" - for the ability to learn anything at all
at this volume. At roughly 19 levels total rather than 675 arms, a few months of
posting is enough to move the estimates.

Q4.9 makes the first few weeks pure exploration, so selection is uniform until
`exploration_posts` observations have accumulated, regardless of epsilon.

Q4.6 is enforced structurally: tone and accuracy are not dimensions, so there is
no weight for the bandit to trade them against.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

from owp.models import NarrativeFormat, VisualStyle
from owp.optimize.arms import POSTING_HOURS, Arm, HookStyle, LengthBucket

#: Q4.9: about three weeks at four posts a week.
EXPLORATION_POSTS = 12
DEFAULT_EPSILON = 0.2

DIMENSIONS: tuple[str, ...] = (
    "format",
    "hook_style",
    "length_bucket",
    "visual_style",
    "posting_hour",
)


def _levels() -> dict[str, list[object]]:
    return {
        "format": list(NarrativeFormat),
        "hook_style": list(HookStyle),
        "length_bucket": list(LengthBucket),
        "visual_style": list(VisualStyle),
        "posting_hour": list(POSTING_HOURS),
    }


@dataclass
class _Stat:
    n: int = 0
    total: float = 0.0

    @property
    def mean(self) -> float:
        return self.total / self.n if self.n else 0.0


@dataclass
class FactoredBandit:
    """Chooses an arm, and learns from scored observations.

    Attributes:
        epsilon: Chance of exploring a random level, per dimension.
        exploration_posts: Observations before exploitation starts (Q4.9).
        rng: Injectable for deterministic tests.
    """

    epsilon: float = DEFAULT_EPSILON
    exploration_posts: int = EXPLORATION_POSTS
    rng: random.Random = field(default_factory=random.Random)
    _stats: dict[str, dict[object, _Stat]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(_Stat))
    )
    _observations: int = 0

    @property
    def observations(self) -> int:
        return self._observations

    @property
    def exploring(self) -> bool:
        """True while still in the forced-exploration phase (Q4.9)."""
        return self._observations < self.exploration_posts

    def select(self) -> Arm:
        """Pick the next arm to try."""
        levels = _levels()
        chosen: dict[str, object] = {}
        for dim in DIMENSIONS:
            options = levels[dim]
            if self.exploring or self.rng.random() < self.epsilon:
                chosen[dim] = self.rng.choice(options)
            else:
                chosen[dim] = max(options, key=lambda lv: self._stats[dim][lv].mean)
        return Arm(
            format=chosen["format"],  # type: ignore[arg-type]
            hook_style=chosen["hook_style"],  # type: ignore[arg-type]
            length_bucket=chosen["length_bucket"],  # type: ignore[arg-type]
            visual_style=chosen["visual_style"],  # type: ignore[arg-type]
            posting_hour=chosen["posting_hour"],  # type: ignore[arg-type]
        )

    def observe(self, arm: Arm, score: float) -> None:
        """Credit `score` to every level the arm used.

        One observation updates all five dimensions, which is what makes the
        factored approach viable at this volume.
        """
        for dim in DIMENSIONS:
            stat = self._stats[dim][getattr(arm, dim)]
            stat.n += 1
            stat.total += score
        self._observations += 1

    def estimates(self, dimension: str) -> dict[object, tuple[int, float]]:
        """Observation count and mean score per level, for the dashboard (Q4.7)."""
        if dimension not in DIMENSIONS:
            raise KeyError(f"unknown dimension {dimension!r}; expected one of {DIMENSIONS}")
        return {lv: (s.n, s.mean) for lv, s in self._stats[dimension].items()}
