from __future__ import annotations

from owp.acquisition.curated import EXPECTED_COUNTS, CuratedTargetSource
from owp.models import Category


def test_expected_counts_match_the_decided_policy_set() -> None:
    assert sum(EXPECTED_COUNTS.values()) == 40


def test_curated_list_loads() -> None:
    assert CuratedTargetSource().targets()


def test_filtering_by_category() -> None:
    social = CuratedTargetSource().targets(Category.SOCIAL)
    assert all(t.category is Category.SOCIAL for t in social)


def test_shortfall_reports_the_placeholder_list_as_incomplete() -> None:
    # The checked-in list is a stub; it must not read as a complete set of 40.
    assert CuratedTargetSource().shortfall()
