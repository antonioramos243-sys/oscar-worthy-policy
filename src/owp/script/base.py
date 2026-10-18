"""Interface for script generation."""

from __future__ import annotations

from typing import Protocol

from owp.models import DataProcessing, NarrativeFormat, PolicyCorpus, Script


class ScriptWriter(Protocol):
    """Writes video scripts from a policy corpus."""

    def practices(self, corpus: PolicyCorpus, *, limit: int) -> list[DataProcessing]:
        """Identify the kinds of data processing worth a video each (Q2.2).

        Each comes back with the verbatim policy text establishing it, because
        the script written from it will be a dramatization and nothing after
        this point is checkable against the document.
        """
        ...

    def write(
        self,
        corpus: PolicyCorpus,
        *,
        processing: DataProcessing,
        format: NarrativeFormat,
        target_seconds: float,
    ) -> Script:
        """Dramatize one kind of processing as one script (Q2.1)."""
        ...


class MisrepresentationError(ValueError):
    """Raised when a script is not licensed by the policy it claims to be about.

    Two cases: a quote that is not in the corpus, and a real person speaking in
    a script whose processing has no evidence behind it. Q2.7 leaves per-line
    accuracy to review, but Q4.6 makes accuracy a hard constraint, and once the
    speaker is a named individual the grounding stops being a matter of degree.
    So this is an error rather than a score.
    """
