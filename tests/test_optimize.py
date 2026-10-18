from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from owp.models import MetricsWindow, PostMetrics
from owp.optimize.arms import POSTING_HOURS, LengthBucket, all_arms
from owp.optimize.bandit import DIMENSIONS, FactoredBandit
from owp.optimize.objective import SHARE_WEIGHT, MetricsUnavailable, informed_score


def metrics(reach: int | None, shares: int | None = None) -> PostMetrics:
    return PostMetrics(
        target_slug="instagram",
        instagram_url="https://instagram.com/p/abc",
        window=MetricsWindow.H24,
        pulled_at=datetime(2026, 10, 20, tzinfo=UTC),
        reach=reach,
        shares=shares,
    )


def test_objective_is_reach_plus_weighted_shares() -> None:
    assert informed_score(metrics(1000, 10)) == 1000 + SHARE_WEIGHT * 10


def test_objective_tolerates_missing_shares() -> None:
    assert informed_score(metrics(500)) == 500


def test_missing_reach_raises_rather_than_scoring_zero() -> None:
    # Scoring a partial record as zero would teach the bandit the variant failed.
    with pytest.raises(MetricsUnavailable):
        informed_score(metrics(None, 5))


def test_posting_hours_respect_quiet_hours() -> None:
    assert all(9 <= h < 22 for h in POSTING_HOURS)


def test_arm_space_size_is_known() -> None:
    assert len(all_arms()) == 135


def test_tone_and_accuracy_are_not_optimizer_variables() -> None:
    # Q4.6: hard constraints, enforced by absence rather than by a weight.
    assert "tone" not in DIMENSIONS
    assert "accuracy" not in DIMENSIONS
    assert len(DIMENSIONS) == 5


def test_explores_uniformly_before_the_threshold() -> None:
    bandit = FactoredBandit(rng=random.Random(1), exploration_posts=10)
    assert bandit.exploring
    for _ in range(9):
        bandit.observe(bandit.select(), 1.0)
    assert bandit.exploring
    bandit.observe(bandit.select(), 1.0)
    assert not bandit.exploring


def test_one_observation_updates_every_dimension() -> None:
    bandit = FactoredBandit(rng=random.Random(2))
    arm = bandit.select()
    bandit.observe(arm, 42.0)
    for dim in DIMENSIONS:
        counts = {n for n, _ in bandit.estimates(dim).values()}
        assert counts == {1}


def test_converges_on_the_better_level() -> None:
    bandit = FactoredBandit(rng=random.Random(3), exploration_posts=5)
    for _ in range(60):
        arm = bandit.select()
        bandit.observe(arm, 100.0 if arm.length_bucket is LengthBucket.SHORT else 10.0)
    picks = [bandit.select().length_bucket for _ in range(200)]
    assert picks.count(LengthBucket.SHORT) > 150


def test_unknown_dimension_rejected() -> None:
    with pytest.raises(KeyError):
        FactoredBandit().estimates("vibes")
