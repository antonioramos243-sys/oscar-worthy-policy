"""Interface for script generation."""

from __future__ import annotations

from typing import Protocol

from owp.models import NarrativeFormat, PolicyCorpus, Script


class ScriptWriter(Protocol):
    """Writes video scripts from a policy corpus."""

    def practices(self, corpus: PolicyCorpus, *, limit: int) -> list[str]:
        """Identify the distinct data practices worth a video each (Q2.2)."""
        ...

    def write(
        self,
        corpus: PolicyCorpus,
        *,
        practice: str,
        format: NarrativeFormat,
        target_seconds: float,
    ) -> Script:
        """Produce one script about one practice."""
        ...


class MisrepresentationError(ValueError):
    """Raised when a script's cited quote is not in the policy corpus.

    Q2.7 does not require citations - review covers accuracy - but it does
    require that videos not misrepresent the policy. Where the writer supplies
    a quote, it must be real. Q4.6 makes accuracy a hard constraint, so this is
    an error rather than a score.
    """
