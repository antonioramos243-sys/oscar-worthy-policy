from __future__ import annotations

from tests.conftest import words

from owp.captions.chunker import cues_from_word_timings
from owp.captions.srt import to_srt


def test_empty_input_yields_no_cues() -> None:
    assert cues_from_word_timings([]) == []


def test_breaks_on_max_words() -> None:
    timings = words(
        ("one", 0.0, 0.2),
        ("two", 0.2, 0.4),
        ("three", 0.4, 0.6),
        ("four", 0.6, 0.8),
        ("five", 0.8, 1.0),
    )
    cues = cues_from_word_timings(timings, max_words=4)
    assert [c.text for c in cues] == ["one two three four", "five"]


def test_breaks_on_pause() -> None:
    # A 0.5s gap before "later" should split the cue even though it is short.
    timings = words(("now", 0.0, 0.2), ("later", 0.7, 0.9))
    cues = cues_from_word_timings(timings, pause_break_seconds=0.35)
    assert [c.text for c in cues] == ["now", "later"]


def test_breaks_on_duration_even_without_pause() -> None:
    # Three slow words with no real gaps; the 2s cap must still split them.
    timings = words(("aaa", 0.0, 1.2), ("bbb", 1.2, 2.4), ("ccc", 2.4, 3.6))
    cues = cues_from_word_timings(timings, max_words=10, max_seconds=2.0)
    assert len(cues) > 1
    assert all(c.end_s - c.start_s <= 2.5 for c in cues)


def test_cue_spans_its_words() -> None:
    cues = cues_from_word_timings(words(("hello", 1.0, 1.3), ("there", 1.3, 1.8)))
    assert cues[0].start_s == 1.0
    assert cues[0].end_s == 1.8


def test_srt_formatting() -> None:
    cues = cues_from_word_timings(words(("hi", 0.0, 0.5)))
    assert to_srt(cues) == "1\n00:00:00,000 --> 00:00:00,500\nhi\n"


def test_srt_of_nothing_is_empty() -> None:
    assert to_srt([]) == ""


def test_srt_handles_minutes_and_hours() -> None:
    cues = cues_from_word_timings(words(("x", 3661.5, 3662.0)))
    assert "01:01:01,500 --> 01:01:02,000" in to_srt(cues)
