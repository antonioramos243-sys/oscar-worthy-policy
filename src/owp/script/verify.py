"""Quote and attribution verification.

`verify_quotes` was never an accuracy gate - Q2.7 puts accuracy on personal
review, and no automated check substitutes for that. It catches one specific
failure review is bad at: a fluent, confident quote the policy never contained.

`verify_attribution` is a gate, and it exists because of what changed on
2026-10-17. The speaker is now the covered company's own CEO, in the first
person, to camera (Q2.1, Q2.4). An uncited line is no longer a possible
mistake about a company; it is a statement attributed to a named real person
who never made it. Review is the wrong place to catch that, so it is made
impossible to render instead.
"""

from __future__ import annotations

from owp.cast import Cast
from owp.models import Citation, PolicyCorpus, Script
from owp.script.base import MisrepresentationError


def verify_quotes(script: Script, corpus: PolicyCorpus) -> None:
    """Check that every quote the script does cite appears verbatim in the corpus.

    Beats without a citation are skipped: they are allowed (Q2.7), and judging
    whether an uncited line misrepresents the policy is review's job.

    Raises:
        MisrepresentationError: if a cited quote is absent from the corpus.
    """
    haystack = " ".join(corpus.text.split())
    cited: list[tuple[str, Citation]] = [
        (f"Beat {index}", beat.citation)
        for index, beat in enumerate(script.beats)
        if beat.citation is not None
    ]
    if script.hook_citation is not None:
        cited.append(("The hook", script.hook_citation))

    for label, citation in cited:
        needle = " ".join(citation.quote.split())
        if needle not in haystack:
            raise MisrepresentationError(
                f"{label} of the {script.target_slug} script quotes text absent from the "
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


def verify_attribution(script: Script, cast: Cast) -> None:
    """Check that nothing is put in a real person's mouth uncited.

    Q2.7's reasoning - citations optional, because every video is reviewed -
    held while the cast was invented characters. It does not hold now that the
    speaker is a named CEO saying "I can do this with your data": an invented
    line is a false quotation of a real person, and the fact that it is
    animated does not change what it asserts.

    Run alongside `verify_quotes`, which proves the citation is genuinely in
    the corpus. Together they mean a real person only ever says, in a video,
    something their own policy says.

    Call `verify_cast` first: this trusts that every named character exists.

    Raises:
        MisrepresentationError: if a beat has no speaker, or if a beat spoken
            by a real person carries no citation.
    """
    for index, beat in enumerate(script.beats):
        if beat.character is None:
            raise MisrepresentationError(
                f"Beat {index} of the {script.target_slug} script has no speaker; "
                "every line of a direct-address video is said by someone (Q2.1)"
            )
        if not cast.get(beat.character).real_person:
            continue
        if beat.citation is None:
            raise MisrepresentationError(
                f"Beat {index} of the {script.target_slug} script puts an uncited line in "
                f"the mouth of {beat.character!r}, a real person: {beat.text[:60]!r}"
            )
