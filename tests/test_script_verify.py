from __future__ import annotations

import pytest

from owp.cast import Cast, Character
from owp.models import Citation, PolicyCorpus, Script
from owp.script.base import MisrepresentationError
from owp.script.verify import verify_attribution, verify_cast, verify_quotes

CAST_IDS = {"zuckerberg", "narrator"}


def ceo_cast() -> Cast:
    """One real person and one invented character: the gate only binds the first."""
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


def test_accepts_evidence_present_in_corpus(script: Script, corpus: PolicyCorpus) -> None:
    verify_quotes(script, corpus)


def test_tolerates_whitespace_differences(script: Script, corpus: PolicyCorpus) -> None:
    script.processing.evidence = [Citation(quote="how   long\nyou view them")]
    verify_quotes(script, corpus)


def test_rejects_evidence_absent_from_corpus(script: Script, corpus: PolicyCorpus) -> None:
    # The one failure review is worst at catching: a confident paraphrase of
    # something the policy never said, offered as the licence for a story.
    script.processing.evidence = [Citation(quote="we sell your data to the highest bidder")]
    with pytest.raises(MisrepresentationError, match="watch-time tracking"):
        verify_quotes(script, corpus)


def test_written_beats_need_no_citation(script: Script, corpus: PolicyCorpus) -> None:
    # The dialogue is a story about what agreeing permits, not a quotation, so
    # there is nothing here to check against the document (Q2.1).
    assert all(beat.citation is None for beat in script.beats)
    verify_quotes(script, corpus)


def test_a_beat_that_does_quote_is_checked(script: Script, corpus: PolicyCorpus) -> None:
    script.beats[0].citation = Citation(quote="a promise the policy never made")
    with pytest.raises(MisrepresentationError, match="Beat 0"):
        verify_quotes(script, corpus)


def test_a_cited_hook_is_checked_too(script: Script, corpus: PolicyCorpus) -> None:
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


# -- attribution: the grounding, not the dialogue ---------------------------


def test_a_grounded_ceo_story_passes(script: Script) -> None:
    verify_attribution(script, ceo_cast())


def test_an_ungrounded_story_in_a_real_persons_mouth_is_refused(script: Script) -> None:
    # The story may be invented; what it dramatizes may not. With no evidence
    # the video is a named man describing something no document establishes.
    script.processing.evidence = []
    with pytest.raises(MisrepresentationError, match="no policy text behind it"):
        verify_attribution(script, ceo_cast())


def test_the_refusal_names_the_person_and_the_processing(script: Script) -> None:
    script.processing.evidence = []
    with pytest.raises(MisrepresentationError, match="zuckerberg") as caught:
        verify_attribution(script, ceo_cast())
    assert "watch-time tracking" in str(caught.value)


def test_an_invented_character_needs_no_grounding(script: Script) -> None:
    # The gate is about real people. An invented narrator falls back to Q2.7,
    # where review covers accuracy.
    for beat in script.beats:
        beat.character = "narrator"
    script.processing.evidence = []
    verify_attribution(script, ceo_cast())


def test_one_real_speaker_among_several_still_needs_grounding(script: Script) -> None:
    script.beats[0].character = "narrator"
    script.processing.evidence = []
    with pytest.raises(MisrepresentationError, match="zuckerberg"):
        verify_attribution(script, ceo_cast())


def test_a_beat_with_no_speaker_is_refused(script: Script) -> None:
    # A direct-address video has somebody saying each line; an unattributed
    # beat would render as the CEO saying it anyway.
    script.beats[0].character = None
    with pytest.raises(MisrepresentationError, match="no speaker"):
        verify_attribution(script, ceo_cast())
