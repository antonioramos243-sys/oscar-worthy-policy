from __future__ import annotations

import pytest

from owp.models import Citation, PolicySnapshot, Script, ScriptBeat
from owp.script.base import UncitedClaimError
from owp.script.verify import verify_citations


def test_accepts_quote_present_in_policy(script: Script, snapshot: PolicySnapshot) -> None:
    verify_citations(script, snapshot)


def test_tolerates_whitespace_differences(script: Script, snapshot: PolicySnapshot) -> None:
    script.beats[1].citation = Citation(quote="how   long\nyou view them")
    verify_citations(script, snapshot)


def test_rejects_quote_absent_from_policy(script: Script, snapshot: PolicySnapshot) -> None:
    script.beats[1].citation = Citation(quote="we sell your data to the highest bidder")
    with pytest.raises(UncitedClaimError, match="instagram"):
        verify_citations(script, snapshot)


def test_uncited_beats_are_left_to_human_review(snapshot: PolicySnapshot, script: Script) -> None:
    # Beat 0 has no citation and is not rejected; that is the reviewer's call.
    script.beats = [ScriptBeat(text="A bold uncited claim.")]
    verify_citations(script, snapshot)
