"""Interfaces for building the target list and fetching policy text."""

from __future__ import annotations

from typing import Protocol

from owp.models import Category, PolicyCorpus, Target


class TargetSource(Protocol):
    """Supplies the ranked list of companies to cover.

    Q1.3: no Sensor Tower license, and no API integration is wanted. Rankings
    are looked up once while building the initial index, so the shipped
    implementation is a curated list rather than a client.
    """

    def targets(self, category: Category | None = None) -> list[Target]:
        """Ranked targets, optionally limited to one category."""
        ...


class PolicyFetcher(Protocol):
    """Turns a target's policy URLs into one merged corpus."""

    def fetch(self, target: Target) -> PolicyCorpus:
        """Fetch and merge every in-scope policy for one target.

        Returns a single corpus, not a document per policy: Q1.4 asks for the
        main, cookie and other policies combined so one video can tell a
        cohesive story about how a platform uses data.

        Raises:
            ExtractionFailed: when no usable text could be extracted. Callers
                fall back to manual upload (Q1.7) rather than retrying.
        """
        ...


class ExtractionFailed(RuntimeError):
    """Raised when a policy page yielded no usable text."""
