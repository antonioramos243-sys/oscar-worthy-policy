from __future__ import annotations

import pytest

from owp.models import Citation, PolicyCorpus, Script, ScriptBeat
from owp.script.base import MisrepresentationError
from owp.script.verify import verify_cast, verify_quotes


def test_accepts_quote_present_in_corpus(script: Script, corpus: PolicyCorpus) -> None:
    verify_quotes(script, corpus)


def test_tolerates_whitespace_differences(script: Script, corpus: PolicyCorpus) -> None:
    script.beats[1].citation = Citation(quote="how   long\nyou view them")
    verify_quotes(script, corpus)


def test_rejects_quote_absent_from_corpus(script: Script, corpus: PolicyCorpus) -> None:
    script.beats[1].citation = Citation(quote="we sell your data to the highest bidder")
    with pytest.raises(MisrepresentationError, match="instagram"):
        verify_quotes(script, corpus)


def test_uncited_beats_are_allowed(corpus: PolicyCorpus, script: Script) -> None:
    # Q2.7: citations are not required, because every video is reviewed.
    script.beats = [ScriptBeat(text="A bold uncited claim.")]
    verify_quotes(script, corpus)


def test_cast_check_accepts_known_characters(script: Script) -> None:
    verify_cast(script, {"narrator", "user"})


def test_cast_check_rejects_unknown_character(script: Script) -> None:
    script.beats[0].character = "the-ceo"
    with pytest.raises(KeyError, match="the-ceo"):
        verify_cast(script, {"narrator", "user"})


def test_cast_check_ignores_beats_with_no_character(script: Script) -> None:
    for beat in script.beats:
        beat.character = None
    verify_cast(script, set())
