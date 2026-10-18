"""Quote and attribution verification.

`verify_quotes` was never an accuracy gate - Q2.7 puts accuracy on personal
review, and no automated check substitutes for that. It catches one specific
failure review is bad at: a fluent, confident quote the policy never contained.

`verify_attribution` is a gate, and it exists because of what changed on
2026-10-17. The speaker is now the covered company's own CEO, in the first
person, to camera (Q2.1), telling the viewer a story about what agreeing to
the policy permits. The lines are written, so they cannot be held to the
document - but the processing they dramatize can be, and must be, because a
named real person is saying it. So the gate holds the grounding, not the
dialogue.
"""

from __future__ import annotations

from owp.cast import Cast
from owp.models import Citation, PolicyCorpus, Script
from owp.script.base import MisrepresentationError


def verify_quotes(script: Script, corpus: PolicyCorpus) -> None:
    """Check that every quote the script supplies appears verbatim in the corpus.

    That covers the evidence behind the processing the video dramatizes, which
    is required, and any beat or hook that quotes the policy outright, which is
    not. Beats without a citation are skipped: the dialogue is written rather
    than quoted, and judging whether a written line goes beyond the policy is
    review's job (Q2.7).

    Raises:
        MisrepresentationError: if a supplied quote is absent from the corpus.
    """
    haystack = " ".join(corpus.text.split())
    cited: list[tuple[str, Citation]] = [
        (f"Evidence for {script.processing.kind!r}", citation)
        for citation in script.processing.evidence
    ]
    cited += [
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
    """Check that a real person's story is licensed by their own policy.

    What the beats say is invention. The CEO is telling the viewer what
    agreeing to the policy lets the company do (Q2.1), and a story that had to
    be quotable would not be a story - so requiring verbatim dialogue would
    rule out the decided format. What is not invention is the processing being
    dramatized, and that is what this holds to the document.

    So a script in which a real, named person speaks must carry at least one
    piece of evidence for the processing it dramatizes; `verify_quotes` then
    proves that evidence is genuinely in the corpus. The result is a creepy
    story about something the policy actually permits, which is the difference
    between commentary on a company and invention about a person.

    Two things this deliberately does not check, because no string comparison
    can, which is why they are review's job (Q2.6) and why the evidence travels
    with the script to the review page (Q3.3):

      - **Alignment.** Whether the story follows from the processing it cites,
        rather than from something adjacent and worse.
      - **Framing.** Whether it stays in capability - what agreeing *lets* the
        company do - instead of asserting that the company did a specific thing
        to this viewer. The first is commentary on a published document; the
        second is a claim of fact about a named individual.

    Call `verify_cast` first: this trusts that every named character exists.

    Raises:
        MisrepresentationError: if a beat has no speaker, or if a real person
            speaks in a script whose processing carries no evidence.
    """
    speakers: list[str] = []
    for index, beat in enumerate(script.beats):
        if beat.character is None:
            raise MisrepresentationError(
                f"Beat {index} of the {script.target_slug} script has no speaker; "
                "every line of a direct-address video is said by someone (Q2.1)"
            )
        speakers.append(beat.character)

    real = [name for name in dict.fromkeys(speakers) if cast.get(name).real_person]
    if not real:
        return

    if not script.processing.evidence:
        raise MisrepresentationError(
            f"The {script.target_slug} script has {', '.join(real)} - a real person - "
            f"dramatizing {script.processing.kind!r}, with no policy text behind it. "
            "A story about a named person needs the processing it dramatizes to be "
            "established by the document (Q2.1)."
        )
