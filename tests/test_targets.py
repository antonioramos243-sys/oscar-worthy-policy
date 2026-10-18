from __future__ import annotations

import json
from pathlib import Path

import pytest

from owp.acquisition.curated import (
    EXPECTED_COUNTS,
    CuratedTargetSource,
    DuplicateTargetError,
)
from owp.models import Category


def test_expected_counts_match_the_decided_policy_set() -> None:
    assert sum(EXPECTED_COUNTS.values()) == 40


def test_curated_list_loads() -> None:
    assert CuratedTargetSource().targets()


def test_filtering_by_category() -> None:
    social = CuratedTargetSource().targets(Category.SOCIAL)
    assert all(t.category is Category.SOCIAL for t in social)


def test_shortfall_reports_the_placeholder_list_as_incomplete() -> None:
    assert CuratedTargetSource().shortfall()


def test_duplicate_slug_across_categories_is_an_error(tmp_path: Path) -> None:
    # Q1.1: a duplicate must be replaced by the next-ranked entry, so its
    # presence in the list is a curation mistake, not a runtime condition.
    path = tmp_path / "targets.json"
    path.write_text(
        json.dumps(
            [
                {"slug": "instagram", "company": "Instagram", "category": "social", "rank": 1},
                {"slug": "instagram", "company": "Instagram", "category": "top_app", "rank": 3},
            ]
        )
    )
    with pytest.raises(DuplicateTargetError, match="instagram"):
        CuratedTargetSource(path).targets()
