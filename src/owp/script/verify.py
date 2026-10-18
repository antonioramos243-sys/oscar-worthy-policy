"""Citation verification: the accuracy gate between generation and rendering."""

from __future__ import annotations

from owp.models import PolicySnapshot, Script
from owp.script.base import UncitedClaimError


def verify_citations(script: Script, snapshot: PolicySnapshot) -> None:
    """Check that every cited quote appears verbatim in the snapshot.

    This is the one check that is cheap, decidable, and worth having before the
    requirements are finalized: an LLM that paraphrases a policy into something
    it does not say is the main accuracy risk, and substring containment catches
    it without judgement calls.

    It does not check that an uncited beat is genuinely non-factual - that is
    what the personal review is for (Q2.7).

    Raises:
        UncitedClaimError: if a quote is absent from the snapshot text.
    """
    haystack = " ".join(snapshot.text.split())
    for index, beat in enumerate(script.beats):
        if beat.citation is None:
            continue
        needle = " ".join(beat.citation.quote.split())
        if needle not in haystack:
            raise UncitedClaimError(
                f"Beat {index} quotes text absent from the {script.target_slug} snapshot "
                f"({snapshot.content_hash[:12]}): {needle[:80]!r}"
            )
