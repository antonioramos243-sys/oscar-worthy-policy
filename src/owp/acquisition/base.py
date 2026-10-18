"""Interfaces for building the target list and fetching policy text."""

from __future__ import annotations

from typing import Protocol

from owp.models import Category, PolicySnapshot, Target


class TargetSource(Protocol):
    """Supplies the ranked list of companies to cover.

    Two implementations are expected: a hand-curated list (good enough for the
    MVP) and a Sensor Tower client once a license is confirmed (Q1.3).
    """

    def targets(self, category: Category | None = None) -> list[Target]:
        """Ranked targets, optionally limited to one category."""
        ...


class PolicyFetcher(Protocol):
    """Turns a target's policy URL into a stored snapshot."""

    def fetch(self, target: Target) -> list[PolicySnapshot]:
        """Fetch every in-scope policy for one target.

        Returns a list because a single company may have several in-scope
        documents (main, cookie, regional) - which is open (Q1.4).

        Raises:
            ExtractionFailed: when no usable text could be extracted. Callers
                should fall back to manual upload (Q1.7) rather than retrying.
        """
        ...


class ExtractionFailed(RuntimeError):
    """Raised when a policy page yielded no usable text."""
