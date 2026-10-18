"""Where a fetched corpus lives on disk.

Q1.6 takes one snapshot per target with no version history, so the path is
keyed by slug alone: a re-fetch overwrites, and there is nothing to prune. The
file is the corpus model as JSON, so loading it back is a validation rather
than a parse - a corpus written by an older build either validates against the
current model or fails loudly.
"""

from __future__ import annotations

from pathlib import Path

from owp.config import Paths
from owp.models import PolicyCorpus


class CorpusNotStored(FileNotFoundError):
    """Raised when no corpus has been fetched for a slug yet."""


def corpus_path(slug: str, *, paths: Paths | None = None) -> Path:
    """Where `slug`'s corpus is stored."""
    return (paths or Paths()).policies / f"{slug}.json"


def save_corpus(corpus: PolicyCorpus, *, paths: Paths | None = None) -> Path:
    """Write a corpus, replacing any earlier snapshot of the same target."""
    resolved = paths or Paths()
    resolved.policies.mkdir(parents=True, exist_ok=True)
    path = corpus_path(corpus.target_slug, paths=resolved)
    path.write_text(corpus.model_dump_json(indent=2) + "\n")
    return path


def load_corpus(slug: str, *, paths: Paths | None = None) -> PolicyCorpus:
    """Read back a stored corpus.

    Raises:
        CorpusNotStored: when the target has not been fetched.
    """
    path = corpus_path(slug, paths=paths)
    if not path.exists():
        raise CorpusNotStored(f"no stored policy corpus for {slug}; run `owp fetch {slug}` first")
    return PolicyCorpus.model_validate_json(path.read_text())


def stored_slugs(*, paths: Paths | None = None) -> list[str]:
    """Slugs that have a stored corpus, sorted."""
    directory = (paths or Paths()).policies
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))
