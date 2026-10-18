"""Fetches policy pages over HTTP, cleans them, and merges them per target.

STUB. The shape is settled now: fetch the US version (Q1.5) of each policy a
target publishes, clean to text, concatenate under per-document headings, and
store once (Q1.6) as cleaned text only (Q1.8).

On robots.txt: Q1.10 says there are no legal constraints to observe, so
`respect_robots` defaults to False. It is kept as a flag because flipping it
costs nothing and privacy-policy pages are almost always crawl-allowed, so
turning it on is unlikely to cost coverage if that decision is revisited.
"""

from __future__ import annotations

import hashlib

from owp.acquisition.base import PolicyFetcher
from owp.models import PolicyCorpus, Target


def content_hash(text: str) -> str:
    """sha256 over cleaned text, so a script can be tied to the corpus it used."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_documents(parts: dict[str, str]) -> str:
    """Join cleaned documents into one corpus under stable headings.

    Headings are kept so the script writer can attribute a practice to the
    cookie policy rather than the main one, and so a reviewer can find it.
    """
    return "\n\n".join(
        f"## {name}\n\n{text.strip()}" for name, text in parts.items() if text.strip()
    )


class HttpPolicyFetcher(PolicyFetcher):
    """Retrieves, cleans and merges policy documents."""

    def __init__(self, *, respect_robots: bool = False, timeout_s: float = 30.0) -> None:
        self.respect_robots = respect_robots
        self.timeout_s = timeout_s

    def fetch(self, target: Target) -> PolicyCorpus:
        raise NotImplementedError(
            "Policy fetching is not implemented. Requirements are settled; this is "
            "straightforward work (fetch, clean, merge) with no open decisions."
        )
