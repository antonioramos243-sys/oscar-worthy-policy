from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owp.models import (
    Citation,
    NarrativeFormat,
    PolicyCorpus,
    PolicyKind,
    PolicySource,
    Script,
    ScriptBeat,
    WordTiming,
)

POLICY_TEXT = (
    "## main_privacy\n\nWe collect information about your activity, including the posts "
    "you view and how long you view them. We may share this information with advertisers."
)


@pytest.fixture
def corpus() -> PolicyCorpus:
    return PolicyCorpus(
        target_slug="instagram",
        fetched_at=datetime(2026, 10, 17, tzinfo=UTC),
        text=POLICY_TEXT,
        sources=[
            PolicySource(kind=PolicyKind.MAIN_PRIVACY, url="https://example.com/privacy"),
            PolicySource(kind=PolicyKind.COOKIE, url="https://example.com/cookies"),
        ],
        content_hash="a" * 64,
    )


@pytest.fixture
def script() -> Script:
    return Script(
        target_slug="instagram",
        content_hash="a" * 64,
        practice="watch-time tracking",
        format=NarrativeFormat.CEO_DIRECT_ADDRESS,
        hook="Can I tell you what you just agreed to?",
        beats=[
            # Every beat is cited because the speaker is a real person (Q2.1).
            ScriptBeat(
                text="I can log every post you look at.",
                citation=Citation(quote="the posts you view"),
                character="zuckerberg",
            ),
            ScriptBeat(
                text="And how long you looked at it.",
                citation=Citation(quote="how long you view them"),
                character="zuckerberg",
            ),
        ],
        estimated_seconds=30.0,
    )


def words(*specs: tuple[str, float, float]) -> list[WordTiming]:
    return [WordTiming(word=w, start_s=s, end_s=e) for w, s, e in specs]
