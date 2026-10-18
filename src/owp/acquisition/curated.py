"""The target list: 40 products ranked by US monthly active users.

Q1.3 settles this as a one-time lookup rather than an API integration, so the
list is data checked into the repo. Q1.2 sets the measure (MAUs or similar) and
Q1.5 the market (US). Q1.1 requires cross-category duplicates to be dropped and
replaced by the next-ranked entry, so a slug must appear at most once.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from owp.models import Category, Target

TARGETS_FILE = Path(__file__).with_name("targets.json")

EXPECTED_COUNTS: dict[Category, int] = {
    Category.SOCIAL: 10,
    Category.DATING: 10,
    Category.AI: 5,
    Category.TOP_APP: 15,
}


class DuplicateTargetError(ValueError):
    """Raised when a product appears in more than one category.

    Q1.1 requires the duplicate to be replaced by the next-ranked entry, so a
    list containing one is a curation error and not something to resolve at
    runtime.
    """


class CuratedTargetSource:
    """Reads targets from a JSON file checked into the repo."""

    def __init__(self, path: Path = TARGETS_FILE) -> None:
        self._path = path

    def targets(self, category: Category | None = None) -> list[Target]:
        raw = json.loads(self._path.read_text())
        items = [Target.model_validate(entry) for entry in raw]

        duplicates = [slug for slug, n in Counter(t.slug for t in items).items() if n > 1]
        if duplicates:
            raise DuplicateTargetError(
                f"{', '.join(sorted(duplicates))} appear in more than one category; "
                "replace with the next-ranked entry (Q1.1)."
            )

        if category is not None:
            items = [t for t in items if t.category is category]
        return sorted(items, key=lambda t: (t.category, t.rank or 10**6))

    def shortfall(self) -> dict[Category, int]:
        """How many targets each category is still missing."""
        have = {c: len(self.targets(c)) for c in Category}
        return {c: EXPECTED_COUNTS[c] - have[c] for c in Category if have[c] < EXPECTED_COUNTS[c]}
