"""Quote verification.

Not an accuracy gate - Q2.7 puts accuracy on personal review, and no automated
check substitutes for that. This catches one specific failure that review is
bad at: a fluent, confident quote that the policy never contained. Cheap to
run, so it runs.
"""

from __future__ import annotations

from owp.models import PolicyCorpus, Script
from owp.script.base import MisrepresentationError


def verify_quotes(script: Script, corpus: PolicyCorpus) -> None:
    """Check that every quote the script does cite appears verbatim in the corpus.

    Beats without a citation are skipped: they are allowed (Q2.7), and judging
    whether an uncited line misrepresents the policy is review's job.

    Raises:
        MisrepresentationError: if a cited quote is absent from the corpus.
    """
    haystack = " ".join(corpus.text.split())
    for index, beat in enumerate(script.beats):
        if beat.citation is None:
            continue
        needle = " ".join(beat.citation.quote.split())
        if needle not in haystack:
            raise MisrepresentationError(
                f"Beat {index} of the {script.target_slug} script quotes text absent from the "
                f"corpus ({corpus.content_hash[:12]}): {needle[:80]!r}"
            )


def verify_cast(script: Script, known_ids: set[str]) -> None:
    """Check that every speaking character exists in the cast.

    Guards character consistency (Q2.4) at the cheapest point: a typo'd or
    invented character id should fail before anything is rendered, not produce
    a stranger in episode 12.

    Raises:
        KeyError: if a beat names a character that is not in the cast.
    """
    for index, beat in enumerate(script.beats):
        if beat.character is not None and beat.character not in known_ids:
            raise KeyError(
                f"Beat {index} names character {beat.character!r}, which is not in the cast"
            )
