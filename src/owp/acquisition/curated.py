"""A hand-maintained target list.

Deliberately the default: it unblocks the whole pipeline without waiting on a
Sensor Tower license (Q1.3). The counts below match the decided policy set -
10 social, 10 dating, 5 AI, 15 top apps - but the *membership* is a placeholder
until the popularity measure and market are chosen (Q1.2), and until we decide
whether cross-category duplicates are replaced by the next-ranked entry (Q1.1).
"""

from __future__ import annotations

import json
from pathlib import Path

from owp.models import Category, Target

TARGETS_FILE = Path(__file__).with_name("targets.json")

EXPECTED_COUNTS: dict[Category, int] = {
    Category.SOCIAL: 10,
    Category.DATING: 10,
    Category.AI: 5,
    Category.TOP_APP: 15,
}


class CuratedTargetSource:
    """Reads targets from a JSON file checked into the repo."""

    def __init__(self, path: Path = TARGETS_FILE) -> None:
        self._path = path

    def targets(self, category: Category | None = None) -> list[Target]:
        raw = json.loads(self._path.read_text())
        items = [Target.model_validate(entry) for entry in raw]
        if category is not None:
            items = [t for t in items if t.category is category]
        return sorted(items, key=lambda t: (t.category, t.rank or 10**6))

    def shortfall(self) -> dict[Category, int]:
        """How many targets each category is still missing.

        Lets the curated list be filled in incrementally without the pipeline
        pretending the set is complete.
        """
        have = {c: len(self.targets(c)) for c in Category}
        return {c: EXPECTED_COUNTS[c] - have[c] for c in Category if have[c] < EXPECTED_COUNTS[c]}
