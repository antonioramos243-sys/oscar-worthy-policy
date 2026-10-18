from __future__ import annotations

import pytest

from owp.cast import Cast, Character
from owp.models import Citation, PolicyCorpus, Script, ScriptBeat
from owp.script.base import MisrepresentationError
from owp.script.verify import verify_attribution, verify_cast, verify_quotes

CAST_IDS = {"zuckerberg", "narrator"}


def ceo_cast() -> Cast:
    """One real person and one invented character, to show the gate only binds one."""
    return Cast(
        characters=[
            Character(
                id="zuckerberg",
                name="Mark Zuckerberg",
                role="Speaks to camera",
                appearance="caricature, not a likeness",
                real_person=True,
                target_slugs=["instagram"],
            ),
            Character(
                id="narrator",
                name="The Narrator",
                role="Not a real person",
                appearance="a",
            ),
        ]
    )


# -- quotes -----------------------------------------------------------------


def test_accepts_quote_present_in_corpus(script: Script, corpus: PolicyCorpus) -> None:
    verify_quotes(script, corpus)


def test_tolerates_whitespace_differences(script: Script, corpus: PolicyCorpus) -> None:
    script.beats[1].citation = Citation(quote="how   long\nyou view them")
    verify_quotes(script, corpus)


def test_rejects_quote_absent_from_corpus(script: Script, corpus: PolicyCorpus) -> None:
    script.beats[1].citation = Citation(quote="we sell your data to the highest bidder")
    with pytest.raises(MisrepresentationError, match="instagram"):
        verify_quotes(script, corpus)


def test_uncited_beats_are_allowed_by_the_quote_check(
    corpus: PolicyCorpus, script: Script
) -> None:
    # Still true of `verify_quotes` itself (Q2.7). What rejects an uncited line
    # in a real person's mouth is `verify_attribution`, below.
    script.beats = [ScriptBeat(text="A bold uncited claim.")]
    verify_quotes(script, corpus)


def test_a_cited_hook_is_checked_too(script: Script, corpus: PolicyCorpus) -> None:
    # The CEO speaks the hook, so it is checked like any other line.
    script.hook_citation = Citation(quote="a promise the policy never made")
    with pytest.raises(MisrepresentationError, match="The hook"):
        verify_quotes(script, corpus)


def test_a_truthful_hook_citation_passes(script: Script, corpus: PolicyCorpus) -> None:
    script.hook_citation = Citation(quote="the posts you view")
    verify_quotes(script, corpus)


# -- cast -------------------------------------------------------------------


def test_cast_check_accepts_known_characters(script: Script) -> None:
    verify_cast(script, CAST_IDS)


def test_cast_check_rejects_unknown_character(script: Script) -> None:
    script.beats[0].character = "someone-else"
    with pytest.raises(KeyError, match="someone-else"):
        verify_cast(script, CAST_IDS)


def test_cast_check_ignores_beats_with_no_character(script: Script) -> None:
    for beat in script.beats:
        beat.character = None
    verify_cast(script, set())


# -- attribution (the gate that came with the CEO cast) ---------------------


def test_a_fully_cited_ceo_script_passes(script: Script) -> None:
    verify_attribution(script, ceo_cast())


def test_an_uncited_line_in_a_real_persons_mouth_is_refused(script: Script) -> None:
    # The point of the gate: this is not a mistake about Meta, it is a
    # sentence attributed to a named man who never said it.
    script.beats[1].citation = None
    with pytest.raises(MisrepresentationError, match="uncited line"):
        verify_attribution(script, ceo_cast())


def test_the_refusal_names_the_person_and_the_line(script: Script) -> None:
    script.beats[0].citation = None
    with pytest.raises(MisrepresentationError, match="zuckerberg") as caught:
        verify_attribution(script, ceo_cast())
    assert "I can log every post" in str(caught.value)


def test_an_invented_character_may_speak_uncited(script: Script) -> None:
    # The gate is about real people, not about citations in general: an
    # invented narrator falls back to Q2.7, where review covers accuracy.
    script.beats[0].character = "narrator"
    script.beats[0].citation = None
    verify_attribution(script, ceo_cast())


def test_a_beat_with_no_speaker_is_refused(script: Script) -> None:
    # A direct-address video has somebody saying each line; an unattributed
    # beat would render as the CEO saying it anyway.
    script.beats[0].character = None
    with pytest.raises(MisrepresentationError, match="no speaker"):
        verify_attribution(script, ceo_cast())
