"""Fetches policy pages over HTTP and reduces them to clean text.

STUB. Before this is implemented, two questions need answers:
  - Q1.10: are we honouring robots.txt, and does each site's ToS need review?
    The fetcher should refuse disallowed paths by default rather than leave
    that to the caller.
  - Q1.8: store raw HTML, cleaned text, or both. The model keeps both.
"""

from __future__ import annotations

import hashlib

from owp.acquisition.base import PolicyFetcher
from owp.models import PolicySnapshot, Target


def content_hash(text: str) -> str:
    """sha256 over cleaned text, used for change detection between snapshots."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class HttpPolicyFetcher(PolicyFetcher):
    """Retrieves and cleans policy documents."""

    def __init__(self, *, respect_robots: bool = True, timeout_s: float = 30.0) -> None:
        self.respect_robots = respect_robots
        self.timeout_s = timeout_s

    def fetch(self, target: Target) -> list[PolicySnapshot]:
        raise NotImplementedError(
            "Policy fetching is not implemented. Blocked on Q1.10 (robots.txt/ToS policy) "
            "and Q1.4 (which of a company's policies are in scope)."
        )
