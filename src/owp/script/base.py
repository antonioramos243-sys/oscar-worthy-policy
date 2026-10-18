"""Interface for script generation."""

from __future__ import annotations

from typing import Protocol

from owp.models import NarrativeFormat, PolicySnapshot, Script


class ScriptWriter(Protocol):
    """Writes a video script from a policy snapshot."""

    def write(
        self,
        snapshot: PolicySnapshot,
        *,
        format: NarrativeFormat,
        target_seconds: float,
    ) -> Script:
        """Produce one script.

        Whether a policy yields one video or several, each on a different
        practice, is open (Q2.2); this signature returns one script per call,
        so either shape works by calling it repeatedly.
        """
        ...


class UncitedClaimError(ValueError):
    """Raised when a generated script makes a factual claim with no supporting quote.

    Accuracy is treated as a hard constraint rather than a score, so this is an
    error and not a warning (Q2.7, Q4.6).
    """
